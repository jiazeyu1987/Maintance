"""Seal real NAS material and retain authenticated readback/close/exit originals."""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from repository_catalog import Catalog
from repository_binding import publish_capture_bindings
from repository_records import (Configuration, Deadline, RepositoryError, absolute,
                                atomic_output, document, exact, pin_file, read_pin,
                                require, safe_path, sign_record, signed_pin, utc,
                                write_new, retain_original)


def native_result(source, bridge):
    require(bridge['schemaVersion'] == 'RepositoryNativeBridgeResult/v1' and bridge['actualExitCode'] == 0, 'REPOSITORY_NATIVE_PROOF_FAILED')
    original = signed_pin(bridge['nativeResponsePin'], source['nativeAuthorityKeyPins'])
    exact(original, 'schemaVersion challenge action sourceConfigPin requestPin result', 'RepositoryNativeResponse/v1')
    require(original['result'] == bridge['result'] and original['action'] == bridge['action'], 'REPOSITORY_NATIVE_PROOF_CHANGED')
    native_request = document(read_pin(original['requestPin']))
    require(native_request['challenge'] == original['challenge'] and native_request['sourceConfigPin'] == original['sourceConfigPin'], 'REPOSITORY_NATIVE_PROOF_REPLAYED')
    return original, original['result']


def native_terminal(source, evidence_pins, request_pin, binding):
    terminals = []
    for reference in evidence_pins:
        value = document(read_pin(reference))
        if value.get('schemaVersion') == 'RepositorySignedRecord/v1':
            verified = signed_pin(reference, source['nativeAuthorityKeyPins'])
            if verified.get('schemaVersion') == 'RepositoryNativeOwnerTerminal/v1':
                terminals.append(verified)
    require(len(terminals) == 1, 'REPOSITORY_NATIVE_ORIGINAL_EXIT_UNPROVEN')
    terminal = terminals[0]
    require(terminal['requestPin'] == request_pin and terminal['binding'] == binding and
            terminal['processTerminated'] is True and terminal['state'] == 'EXITED' and
            type(terminal['actualExitCode']) is int and terminal['actualExitCode'] == 0,
            'REPOSITORY_NATIVE_ORIGINAL_EXIT_UNPROVEN')
    identity = terminal['ownerIdentity']
    require(type(identity) is dict and set(identity) == {'pid', 'processStartTicks', 'hostBootId',
            'pidNamespace', 'mountNamespace', 'programPin'} and
            type(identity['pid']) is int and identity['pid'] > 0 and
            type(identity['processStartTicks']) is int and identity['processStartTicks'] > 0 and
            all(type(identity[k]) is str and identity[k] for k in ('hostBootId', 'pidNamespace', 'mountNamespace')),
            'REPOSITORY_NATIVE_ORIGINAL_PROCESS_UNPROVEN')
    peer = document(read_pin(source['nativePeerConfigPin']))['payload']
    if source['schemaVersion'] == 'RepositoryNativeBackupSource/v1':
        host = document(read_pin(source['executionHostPin']))
    else:
        carrier = document(read_pin(source['wslCarrierConfigPin']))
        host = document(read_pin(carrier['executionHostPin']))
    require(identity['programPin'] == peer['ownerEntryPin'] and identity['hostBootId'] == host['bootId'],
            'REPOSITORY_NATIVE_ORIGINAL_PROCESS_UNPROVEN')
    read_pin(identity['programPin'])
    return terminal


def seal(config, request_pin, source, facts, deadline):
    request = document(read_pin(request_pin))
    config.request(request)
    config.authorization(request, request['sourceOrTargetRef'])
    original, capture = native_result(source, facts['nativeProof'])
    exact(capture, 'schemaVersion repositoryId operationId requestPin sourceConfigPin binding originalProcessPin archiveHeaderPin payloadTree metadata nativeEvidencePins', 'RepositoryNativeCapture/v1')
    require(original['action'] == 'observe-capture' and original['sourceConfigPin'] == request['sourceOrTargetRef'] and capture['requestPin'] == request_pin and capture['operationId'] == request['operationId'] and capture['repositoryId'] == config.value['repositoryId'], 'REPOSITORY_NATIVE_CAPTURE_SCOPE_MISMATCH')
    require(capture['sourceConfigPin'] == request['sourceOrTargetRef'] and capture['binding'] == facts['binding'] and capture['originalProcessPin'] == facts['originalProcessPin'] and capture['archiveHeaderPin'] == facts['archiveHeaderPin'] and capture['payloadTree'] == facts['expectedEntries'] and capture['nativeEvidencePins'], 'REPOSITORY_NATIVE_CAPTURE_MISMATCH')
    process = document(read_pin(facts['originalProcessPin']))
    require(process['ownerPid'] == facts['ownerPid'] and process['requestPin'] == request_pin and process['binding'] == facts['binding'], 'REPOSITORY_PROCESS_BINDING_MISMATCH')
    metadata = capture['metadata']
    exact(metadata, 'schemaVersion backupId generationId pointType parentPointPins commonRecoveryPoint sourceIdentityPin createdAt versionPins toolPins', 'RepositoryCaptureMetadata/v1')
    require(all(type(metadata[key]) is str and metadata[key] for key in ('backupId', 'generationId', 'commonRecoveryPoint')), 'REPOSITORY_CAPTURE_METADATA_REQUIRED')
    catalog = Catalog(config, deadline)
    parents = [row[0] for row in catalog.chain(request['selectedPointPin'])] if request['action'] == 'BACKUP_INCREMENTAL' else []
    require(metadata['parentPointPins'] == parents and metadata['pointType'] == ('INCREMENTAL' if parents else 'FULL'), 'REPOSITORY_CAPTURE_KIND_OR_PARENT_MISMATCH')
    if parents:
        require(metadata['generationId'] == catalog.load(parents[-1])[0]['generationId'], 'REPOSITORY_CAPTURE_GENERATION_MISMATCH')
    archive = safe_path(facts['archive']['archivePath'])
    require(archive.parent == catalog.archives and archive.name == 'prod-' + facts['binding']['attemptId'], 'REPOSITORY_PUBLICATION_TARGET_ESCAPED')
    require(facts['archive']['transportVerified'] is True and facts['archive']['serverDurabilityVerified'] is False, 'REPOSITORY_NAS_TRANSPORT_UNPROVEN')
    # Metadata is immutable. Interrupted work stays visible without a COMPLETE point.
    sidecar = archive / '.repository'
    sidecar.mkdir()
    retain_original(sidecar / 'original-process.json', facts['originalProcessPin'])
    process_pin = facts['originalProcessPin']
    retain_original(sidecar / 'native-capture.json', facts['nativeProof']['nativeResponsePin'], 128 * 1024 * 1024)
    capture_original_pin = facts['nativeProof']['nativeResponsePin']
    tree_pin = write_new(sidecar / 'payload-tree.json', capture['payloadTree'])
    files = []
    for relative, spec in sorted(capture['payloadTree'].items()):
        deadline.check()
        if spec != 'directory':
            files.append(pin_file(archive / relative, deadline))
    manifest = {key: metadata[key] for key in ('backupId', 'generationId', 'pointType', 'parentPointPins', 'commonRecoveryPoint', 'sourceIdentityPin', 'createdAt', 'versionPins', 'toolPins')}
    manifest.update(schemaVersion='RepositoryManifest/v1', payloadRefs=files, payloadTreePin=tree_pin, copyProtectionPin=config.copy_protection())
    manifest_pin = write_new(sidecar / 'manifest.json', manifest)
    candidate = {key: manifest[key] for key in ('backupId', 'generationId', 'pointType', 'parentPointPins', 'commonRecoveryPoint', 'payloadRefs')}
    candidate['manifestPin'] = manifest_pin
    checked, actual_archive = catalog.manifest(candidate)
    catalog.payload(candidate, checked, actual_archive)
    return {'schemaVersion': 'RepositorySealedMaterial/v1', 'manifestPin': manifest_pin, 'payloadTreePin': tree_pin, 'payloadRefs': files, 'originalProcessPin': process_pin, 'nativeCaptureResponsePin': capture_original_pin, 'binding': facts['binding']}


def complete(config, request_pin, source, facts, deadline):
    request = document(read_pin(request_pin))
    config.request(request)
    config.authorization(request, request['sourceOrTargetRef'])
    material = facts['material']
    manifest = document(read_pin(material['manifestPin']))
    terminal = facts['terminal']
    process = document(read_pin(material['originalProcessPin']))
    require(type(terminal['actualExitCode']) is int and terminal['actualExitCode'] == 0 and terminal['processTerminated'] is True and terminal['rawTerminalVerified'] is True and terminal['originalOwnerPid'] == process['ownerPid'] == facts['ownerPid'], 'REPOSITORY_ORIGINAL_EXIT_UNKNOWN')
    require(terminal['attemptId'] == material['binding']['attemptId'] and terminal['sourceContextSha256'] == material['binding']['sourceContextSha256'] and terminal['treeDigest'] == facts['archive']['treeDigest'], 'REPOSITORY_TERMINAL_BINDING_MISMATCH')
    close = terminal['closeResponse']
    require(close['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF' and close['attemptId'] == terminal['attemptId'] and close['sourceContextSha256'] == terminal['sourceContextSha256'] and close['treeDigest'] == terminal['treeDigest'], 'REPOSITORY_EXACT_CLOSE_UNPROVEN')
    original, readback = native_result(source, facts['readbackProof'])
    exact(readback, 'schemaVersion binding archivePath payloadTree manifestPin payloadTreePin payloadRefs independentConnectionId nativeEvidencePins serverDurabilityVerified originalRecordsPin', 'RepositoryNativeReadback/v1')
    require(original['action'] == 'observe-readback' and original['sourceConfigPin'] == request['sourceOrTargetRef'] and readback['binding'] == material['binding'] and absolute(readback['archivePath']) == absolute(facts['archive']['archivePath']) and readback['manifestPin'] == material['manifestPin'] and readback['payloadTreePin'] == material['payloadTreePin'] and readback['payloadRefs'] == material['payloadRefs'] and readback['payloadTree'] == document(read_pin(material['payloadTreePin'])) and type(readback['independentConnectionId']) is str and readback['independentConnectionId'] and readback['nativeEvidencePins'] and readback['serverDurabilityVerified'] is False, 'REPOSITORY_INDEPENDENT_READBACK_UNPROVEN')
    native_terminal(source, readback['nativeEvidencePins'], request_pin, material['binding'])
    candidate = {key: manifest[key] for key in ('backupId', 'generationId', 'pointType', 'parentPointPins', 'commonRecoveryPoint', 'payloadRefs')}
    candidate['manifestPin'] = material['manifestPin']
    catalog = Catalog(config, deadline)
    checked, archive = catalog.manifest(candidate)
    catalog.payload(candidate, checked, archive)
    bindings = publish_capture_bindings(config, catalog, request, material['manifestPin'], readback, deadline)
    sidecar = Path(material['manifestPin']['path']).parent
    retain_original(sidecar / 'native-readback.json', facts['readbackProof']['nativeResponsePin'], 128 * 1024 * 1024)
    readback_original_pin = facts['readbackProof']['nativeResponsePin']
    common = {'repositoryId': config.value['repositoryId'], 'operationId': request['operationId'], 'backupId': manifest['backupId'], 'manifestPin': material['manifestPin'], 'originalProcessPin': material['originalProcessPin']}
    records = {
        'readbackEvidencePin': dict(common, schemaVersion='RepositoryReadback/v1', independentConnection=True, payloadRefs=material['payloadRefs'], serverDurabilityVerified=False, nativeResponsePin=readback_original_pin, **bindings),
        'ownerCloseEvidencePin': dict(common, schemaVersion='RepositoryOwnerClose/v1', exactReaderCloseVerified=True, sourceFinalGuardVerified=True, closeResponse=close, nativeCaptureResponsePin=material['nativeCaptureResponsePin']),
        'originalExitEvidencePin': dict(common, schemaVersion='RepositoryOriginalExit/v1', actualExitCode=terminal['actualExitCode'], rawTerminalVerified=True, processTerminated=True, terminal=terminal)}
    publication = {'schemaVersion': 'RepositoryPublication/v1', 'manifestPin': material['manifestPin'], 'actualExitCode': terminal['actualExitCode'], **bindings}
    for field, record in records.items():
        publication[field] = write_new(sidecar / (field + '.json'), sign_record(record, source['evidenceSigningKeyPin'], config.value['evidenceKeyPins']))
    point = {key: manifest[key] for key in ('backupId', 'generationId', 'pointType', 'parentPointPins', 'commonRecoveryPoint', 'payloadRefs')}
    point.update({key: value for key, value in publication.items() if key.endswith('Pin')})
    Catalog(config, deadline).evidence(point)
    config.current()
    return publication


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('configuration', 'configuration-sha256', 'request', 'request-sha256', 'facts', 'output', 'action'):
        parser.add_argument('--' + field, required=True)
    args = parser.parse_args()
    configuration_pin, request_pin = pin_file(absolute(args.configuration)), pin_file(absolute(args.request))
    require(configuration_pin['sha256'] == args.configuration_sha256 and request_pin['sha256'] == args.request_sha256, 'REPOSITORY_PUBLICATION_INPUT_CHANGED')
    config = Configuration(configuration_pin)
    request = document(read_pin(request_pin))
    source = document(read_pin(request['sourceOrTargetRef']))
    facts = document(read_pin(pin_file(absolute(args.facts))))
    deadline = Deadline(facts['remainingMilliseconds'])
    if args.action == 'seal':
        result = seal(config, request_pin, source, facts, deadline)
    elif args.action == 'complete':
        result = complete(config, request_pin, source, facts, deadline)
    elif args.action == 'verify-terminal':
        publication = document(read_pin(facts['publicationPin']))
        manifest = document(read_pin(publication['manifestPin']))
        point = {key: manifest[key] for key in ('backupId', 'generationId', 'pointType', 'parentPointPins', 'commonRecoveryPoint', 'payloadRefs')}
        point.update({key: value for key, value in publication.items() if key.endswith('Pin')})
        catalog = Catalog(config, deadline)
        checked, archive = catalog.manifest(point)
        catalog.payload(point, checked, archive)
        catalog.evidence(point)
        config.authorization(request, request['sourceOrTargetRef'])
        result = {'schemaVersion': 'RepositoryTerminalVerification/v1', 'publicationPin': facts['publicationPin']}
    else:
        raise RepositoryError('REPOSITORY_PUBLICATION_ACTION_INVALID')
    atomic_output(absolute(args.output), result)


if __name__ == '__main__':
    import sys
    try:
        main()
    except Exception as error:
        print(error.code if isinstance(error, RepositoryError) else 'REPOSITORY_PUBLISH_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(1)
