"""Task-local immutable evidence contracts; importing performs no I/O."""
import datetime
import hashlib
import json
from pathlib import Path
import re

from common import PRIVATE, SOURCE


def read(task, name):
    assert type(name) is str and Path(name).name == name and name.endswith('.json'), 'TASK_EVIDENCE_NAME_INVALID'
    return json.loads((task / name).read_text(encoding='utf-8'))


def moment(value):
    result = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    assert result.tzinfo is not None, 'EVIDENCE_TIME_ZONE_REQUIRED'
    return result


def file_pin(task, name):
    read(task, name)
    raw = (task / name).read_bytes()
    return dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def pinned(task, pin):
    assert set(pin) == {'file', 'bytes', 'sha256'}, 'EVIDENCE_PIN_INVALID'
    assert file_pin(task, pin['file']) == pin, 'ORIGINAL_EVIDENCE_CHANGED'
    return read(task, pin['file'])


def terminal_observation(task, kind, request):
    assert kind in ('restore-58-r4', 'restore-59'), 'UNREVIEWED_TERMINAL_KIND'
    selected = read(task, kind + '-terminal-observation-selection.json')
    retained = read(task, kind + '-terminal-failed-observations.json')
    assert selected['schemaVersion'] == 'TaskReadonlyObservationSelection/v1'
    assert retained['schemaVersion'] == 'TaskReadonlyObservations/v1'
    assert selected['operationId'] == retained['operationId'] == request['operationId']
    pins = retained['failed'] + [selected['selectedPin']]
    assert len({pin['file'] for pin in pins}) == len(pins), 'OBSERVATION_PIN_DUPLICATE'
    required = [kind + '-ui-readonly-terminal.json', kind + '-ui-readonly-terminal-r2.json']
    if kind == 'restore-58-r4':
        required.append(kind + '-ui-readonly-terminal-r3.json')
    assert set(required) <= {pin['file'] for pin in retained['failed']}, 'ORIGINAL_FAILURE_OMITTED'
    previous = None
    for index, pin in enumerate(pins):
        match = re.fullmatch(re.escape(kind) + r'-ui-readonly-terminal(?:-r([2-9]|[1-9][0-9]+))?\.json', pin['file'])
        assert match and int(match.group(1) or 1) == index + 1, 'ORIGINAL_OBSERVATION_SEQUENCE_GAP'
        value = pinned(task, pin)
        assert value['operationId'] == request['operationId'] and value['businessWrites'] == 0
        assert previous is None or moment(value['startedAt']) > moment(previous['observedAt']), 'OBSERVATION_SEQUENCE_INVALID'
        if index < len(pins) - 1:
            assert value['status'] == 'FAIL' and value['error']
            if 'request' in value:
                assert value['request'] == request
        previous = value
    assert previous['status'] == 'PASS' and previous['phase'] == 'terminal' and previous['request'] == request
    assert previous['logs'] and '步骤日志读取失败' not in previous['logs'] and 'ENTRY_REQUEST_TIMEOUT' not in previous['logs']
    return previous


def build_entry(task, private, name):
    assert re.fullmatch(r'release-build-[0-9a-f]{7}\.json', name), 'EXPLICIT_BUILD_REPORT_REQUIRED'
    report = read(task, name)
    commit = report['targetCommit']
    assert re.fullmatch('[0-9a-f]{40}', commit) and name == 'release-build-' + commit[:7] + '.json'
    generation = commit[:7]
    expected = (private / ('release-' + generation)).resolve()
    assert Path(report['worktree']).resolve() == expected and expected.parent == private.resolve(), 'BUILD_PATH_OUT_OF_SCOPE'
    assert report['status'] == 'PASS' and report['allFilesShaAndCompileVerified'] is True
    assert type(report['fileCount']) is int and report['fileCount'] > 0
    assert report['newCommits'] is False and report['mergeRequired'] is False and report['deleted'] is False
    for key in ('packageSha256', 'fileManifestSha256'):
        assert re.fullmatch('[0-9a-f]{64}', report[key]), 'BUILD_PACKAGE_PIN_INVALID'
    return dict(generation=generation, reportPin=file_pin(task, name), targetCommit=commit,
                worktree=str(expected), package=str((private / ('package-' + generation) / 'backup-restore-standard.tgz').resolve()),
                packageSha256=report['packageSha256'], fileManifestSha256=report['fileManifestSha256'], fileCount=report['fileCount'])


def validate_build_manifest(task, private, manifest):
    assert manifest['schemaVersion'] == 'TaskOwnedBuilds/v1' and manifest['taskId'] == task.name
    entries = manifest['builds']
    assert isinstance(entries, list) and entries, 'EXPLICIT_OWNED_BUILDS_REQUIRED'
    assert len({entry['generation'] for entry in entries}) == len(entries), 'DUPLICATE_BUILD_GENERATION'
    assert len({str(Path(entry['worktree']).resolve()) for entry in entries}) == len(entries), 'DUPLICATE_BUILD_PATH'
    for entry in entries:
        pinned(task, entry['reportPin'])
        assert entry == build_entry(task, private, entry['reportPin']['file']), 'BUILD_MANIFEST_IDENTITY_CHANGED'
    return entries


def owned_builds(task, private=PRIVATE):
    return validate_build_manifest(task, private, read(task, 'task-owned-builds.json'))


def controller_generation(installation, index, task=None):
    """Normalize only the known initial pair or the explicit successor contract."""
    assert index in (0, 1) and len(installation['controllers']) == 2
    task = Path(__file__).resolve().parent if task is None else Path(task)
    role = ('SOURCE', 'MAIN_TARGET')[index]
    if installation.get('schemaVersion') == 'AutomaticSourceControlUpgrade/v1':
        rows = installation['controllerGenerations']
        assert len(rows) == 2 and rows[index]['role'] == role, 'CONTROLLER_GENERATION_ROLE_INVALID'
        result = dict(rows[index])
        if index == 0:
            assert all(result[key] == installation[key] for key in
                       ('sourceCommit', 'packageSha256', 'fileManifestSha256', 'fileCount'))
        return result
    assert installation.get('schemaVersion') is None and installation['sourceCommit'] == \
        '0d445782dc06995b3c84b1b45146ea4b75483f92', 'UNKNOWN_INITIAL_INSTALLATION'
    return dict(role=role, **{key: installation[key] for key in
        ('sourceCommit', 'packageSha256', 'fileManifestSha256', 'fileCount')},
        buildPin=file_pin(task, 'release-build-' + installation['sourceCommit'][:7] + '.json'))


def validate_source_successor(task, source, visited=None):
    assert source['schemaVersion'] == 'AutomaticSourceControlUpgrade/v1' and source['status'] == 'PASS'
    visited = set() if visited is None else visited
    assert source['sourceCommit'] not in visited, 'SOURCE_INSTALLATION_CYCLE'
    visited.add(source['sourceCommit'])
    previous = pinned(task, source['predecessorInstallationPin'])
    if previous.get('schemaVersion') == 'AutomaticSourceControlUpgrade/v1':
        validate_source_successor(task, previous, visited)
    else:
        controller_generation(previous, 0, task)
        assert source['predecessorInstallationPin']['file'] == 'automatic-control-installation-57.json'
    assert previous['status'] == 'PASS' and previous['sourceCommit'] != source['sourceCommit']
    assert source['controllers'][1] == previous['controllers'][1], 'RETAINED_TARGET_CHANGED'
    assert source['policy'] == previous['policy'] and source['epoch'] == previous['epoch'], 'PHYSICAL_SOURCE_EPOCH_CHANGED'
    assert source['epoch']['state'] == 'READY'
    assert source['controllers'][0]['service'] == previous['controllers'][0]['service']
    assert source['controllers'][0]['previousPid'] == previous['controllers'][0]['pid']
    assert source['controllers'][0]['pid'] != previous['controllers'][0]['pid']
    assert source['controllers'][0]['engine'] != previous['controllers'][0]['engine']
    for field in ('retainedTargetControlUnchanged', 'epochUnchanged', 'physicalSourceUnchanged',
                  'previousGenerationsRetained', 'allOriginalContainersUnchanged', 'fstabAndProtectedMountsUnchanged'):
        assert source[field] is True, 'SOURCE_SUCCESSOR_PRESERVATION_REQUIRED_' + field
    assert source['backupPerformed'] is False and source['restorePerformed'] is False
    for index in (0, 1):
        generation = controller_generation(source, index, task)
        build = pinned(task, generation['buildPin'])
        assert generation['buildPin']['file'] == 'release-build-' + generation['sourceCommit'][:7] + '.json'
        assert build['status'] == 'PASS' and build['targetCommit'] == generation['sourceCommit']
        assert all(generation[key] == build[key] for key in ('packageSha256', 'fileManifestSha256', 'fileCount'))
        if index == 0:
            assert generation['buildPin'] == source['buildPin']
        else:
            retained = pinned(task, generation['installationPin'])
            original = controller_generation(retained, 1, task)
            assert all(generation[key] == original[key] for key in
                ('sourceCommit', 'packageSha256', 'fileManifestSha256', 'fileCount', 'buildPin'))
            assert retained['controllers'][1] == source['controllers'][1]
    spug = pinned(task, source['retainedSpugInstallationPin'])
    assert spug['status'] == 'PASS' and len(spug['files']) == 11


def validate_native_dispatch(audit):
    value = audit['nativeDispatch']
    assert value['launcherActualExitCode'] == audit['nativeLauncherExitCode']
    assert value['ownerActualExitCode'] == 0 and value['ownerState'] == 'SUCCEEDED'
    assert (value['launcherActualExitCode'], value['launcherState'], value['resolution']) in (
        (0, 'SUCCEEDED', 'OWNER_TERMINAL_RETURNED_SYNCHRONOUSLY'),
        (2, 'TERMINAL_UNKNOWN', 'ORIGINAL_OWNER_TERMINAL_AFTER_ASYNC_REPLY'))
    pin = value['originalReplyPin']
    assert isinstance(pin, dict) and set(pin) == {'path', 'bytes', 'sha256'}
    assert isinstance(pin['path'], str) and pin['path'].startswith('/') and pin['bytes'] > 0
    assert re.fullmatch('[0-9a-f]{64}', pin['sha256'])


def current_installations(task):
    selection = read(task, 'automatic-current-installations.json')
    assert selection['schemaVersion'] in ('TaskCurrentInstallations/v1', 'TaskCurrentInstallations/v2')
    assert set(selection['targets']) == {'58', '59'}
    source = pinned(task, selection['source57'])
    spug = pinned(task, selection['spug'])
    validate_source_spug(task, source, spug)
    if source.get('schemaVersion') == 'AutomaticSourceControlUpgrade/v1':
        assert selection['schemaVersion'] == 'TaskCurrentInstallations/v2', 'MIXED_GENERATION_SELECTION_REQUIRED'
    targets = {}
    for suffix, pin in selection['targets'].items():
        installed = pinned(task, pin)
        assert installed['status'] == 'PASS' and installed['host'] == '172.30.30.' + suffix
        retained_generation = controller_generation(source, 1, task)
        assert all(installed[key] == retained_generation[key] for key in
                   ('sourceCommit', 'packageSha256', 'fileManifestSha256', 'fileCount')), 'RETAINED_REMOTE_TARGET_GENERATION_CHANGED'
        build = read(task, 'release-build-' + installed['sourceCommit'][:7] + '.json')
        assert build['status'] == 'PASS' and build['targetCommit'] == installed['sourceCommit']
        assert installed['targetConfigRef'] == 'intruoyi-main-' + suffix + '-safe-restore-20261104-v1'
        assert all(installed[key] == build[key] for key in ('packageSha256', 'fileManifestSha256', 'fileCount'))
        for field in ('actualSelectionVerifiedBeforeActivation', 'actualSelectionVerifiedAfterActivation',
                      'actualHealthContractVerified', 'actualPackagedConstructorVerified', 'constructorStopsBeforeDatabaseIO',
                      'targetAndSourceConfigurationUnchanged', 'source57MetadataUnchanged',
                      'allBusinessDefinitionsAndRuntimeUnchanged', 'fstabAndProtectedMountsUnchanged', 'previousGenerationsRetained'):
            assert installed[field] is True, 'CURRENT_TARGET_INSTALLATION_NOT_PROVEN_' + field
        assert installed['restoreDispatched'] is False and installed['backupDispatched'] is False
        assert installed['oldControlPid'] != installed['controlPid'] and installed['liveMaxOpenFiles'] == 65536
        custody = installed['installationReceiptCustody']
        assert custody['status'] == 'PASS' and custody['activationCount'] == len(installed['extendedCustody']['steps'])
        assert custody['selectedCurrentReceiptPin'] == installed['currentReceiptPin']
        assert custody['allReceiptAndConfigurationPinsVerified'] and custody['allHistoricalSourceAndTargetDefinitionsUnchanged']
        if suffix == '58':
            assert installed['epochStatus'] == 'NOT_ENABLED_NO_REGISTERED_MAIN_SOURCE_IDENTITY' and installed['epochPolicy'] is None
        else:
            assert installed['epochStatus'] == 'REGISTER_WITH_TARGET_ONLY' and installed['epoch']['state'] == 'READY'
        targets[suffix] = installed
    catalogue = pinned(task, selection['catalogueInstallation'])
    observed = pinned(task, selection['catalogueReadonlyObservation'])
    catalogue_observation_selection(task, selection['catalogueReadonlyObservation'])
    assert catalogue['status'] == 'PASS' and re.fullmatch('[0-9a-f]{40}', catalogue['sourceCommit'])
    builds = {entry['targetCommit']: entry for entry in owned_builds(task)}
    assert catalogue['sourceCommit'] in builds, 'CATALOGUE_BUILD_NOT_EXPLICITLY_OWNED'
    assert Path(catalogue['buildWorktree']).resolve() == Path(builds[catalogue['sourceCommit']]['worktree']).resolve()
    for field in ('allOriginalJobsPreserved', 'existingConfigurationPreserved', 'unrelated18081Preserved', 'originalSourceControlPidPreserved'):
        assert catalogue[field] is True, 'CATALOGUE_INSTALLATION_PRESERVATION_REQUIRED'
    validate_catalogue_observation(observed, catalogue)
    return dict(selection=selection, source57=source, spug=spug, targets=targets, catalogue=catalogue, catalogueObservation=observed)


def validate_catalogue_observation(observed, installed):
    assert observed.get('schemaVersion') == 'CatalogueIdentityReadonlyUi/v1', 'DEDICATED_CATALOGUE_UI_OBSERVATION_REQUIRED'
    assert observed['status'] == 'PASS' and observed['httpStatus'] == observed['documentHttpStatus'] == 200
    assert observed['sourceCommit'] == installed['sourceCommit']
    assert observed['actualPageRequest'] and observed['realBrowser'] and observed['identityVerified']
    assert observed['authentication'] == 'fresh-real-ui-login' and observed['authPosts'] == 1 and not observed['blockedRequests']
    assert observed['backupPageInitialized'] and observed['businessWrites'] == 0 and not observed['pageErrors']
    assert observed['itemCount'] > 0 and observed['visibleRowCount'] > 0
    assert observed['displayedTotal'] == observed['itemCount'] and observed['refreshing'] is False and observed['complete'] is True
    assert not observed['catalogueErrors'] and not observed['visibleProblem']
    assert moment(observed['startedAt']) >= moment(installed['observedAt']), 'CATALOGUE_POSTINSTALL_PAGE_OBSERVATION_REQUIRED'


def catalogue_observation_selection(task, selected_pin):
    selection = read(task, 'catalogue-identity-readonly-selection.json')
    assert selection['schemaVersion'] == 'TaskCatalogueReadonlySelection/v1' and selection['selectedPin'] == selected_pin
    assert selection['failed'], 'ORIGINAL_CATALOGUE_FAILURE_REQUIRED'
    previous = None
    pins = selection['failed'] + [selected_pin]
    for index, pin in enumerate(pins, 1):
        expected = 'catalogue-identity-readonly-verification' + ('' if index == 1 else '-r' + str(index)) + '.json'
        assert pin['file'] == expected, 'CATALOGUE_OBSERVATION_SEQUENCE_GAP'
        value = pinned(task, pin)
        assert value['businessWrites'] == 0 and value['schemaVersion'] == 'CatalogueIdentityReadonlyUi/v1'
        assert previous is None or moment(value['startedAt']) > moment(previous['observedAt'])
        assert value['status'] == ('PASS' if index == len(pins) else 'FAIL')
        previous = value
    return previous


def validate_source_spug(task, source, spug):
    assert source['status'] == spug['status'] == 'PASS'
    if source.get('schemaVersion') == 'AutomaticSourceControlUpgrade/v1':
        validate_source_successor(task, source)
        assert pinned(task, source['retainedSpugInstallationPin']) == spug
    else:
        assert source['sourceCommit'] == spug['sourceCommit']
    build = read(task, 'release-build-' + source['sourceCommit'][:7] + '.json')
    assert build['status'] == 'PASS' and build['targetCommit'] == source['sourceCommit']
    assert source['packageSha256'] == build['packageSha256'] and source['fileManifestSha256'] == build['fileManifestSha256']
    assert source['epoch']['state'] == 'READY' and source['allOriginalContainersUnchanged'] and source['fstabAndProtectedMountsUnchanged']
    assert source['backupPerformed'] is False and source['restorePerformed'] is False
    assert len(source['controllers']) == 2 and len({row['service'] for row in source['controllers']}) == 2
    assert spug['runtime'].replace('\\', '/').lower() == 'c:/spug/runtime/ops/spug'
    assert len(spug['files']) == 11 and spug['newEntryPid'] != spug['previousEntryPid']
    assert spug['oldFilesPreserved'] and spug['nginxConfigurationTested'] and not spug['sharedServiceRestarted']
    assert not spug['backupPerformed'] and not spug['restorePerformed']


def validate_source_restoration(task, kind, restored, source, request, audit, installation_pin=None):
    assert restored.get('schemaVersion') == 'AutomaticSourceRestoration/v1', 'AUTOMATIC_INDEPENDENT_SOURCE_REPORT_REQUIRED'
    assert restored['status'] == 'PASS' and restored['kind'] == kind
    assert restored['operationId'] == restored['backupOperationId'] == request['operationId']
    assert restored['sourceConfigRef'] == SOURCE and restored['installationCommit'] == source['sourceCommit']
    assert restored['sourceIdentity'] == source['policy']['sourceIdentity']
    assert restored['sourceEpoch'] == audit['sourceEpoch'] and restored['epochId'] == source['epoch']['epochId']
    assert restored['databaseUuid'] == source['policy']['databaseUuid']
    assert restored['eventScheduler'] == 'ON' and restored['readOnly'] == restored['superReadOnly'] == '0'
    for key in ('originalGlobalStateRestored', 'redisPongVerified', 'sourceIdle', 'sourceLockVerified',
                'sourceServicesHealthy', 'noRemoteMutation', 'strictBinlogToolStillVerified', 'registeredExporterTemporaryContractVerified'):
        assert restored[key] is True, 'SOURCE_RESTORATION_UNVERIFIED_' + key
    assert restored['workerCount'] == 0 and restored['installedEngineFilesVerified'] == source['fileCount']
    assert len(restored['services']) == 5 and len({row['id'] for row in restored['services']}) == 5
    assert all(row['running'] for row in restored['services'])
    assert set(restored['semanticHealth']) == {'minio', 'backend', 'frontend'}
    assert all(row['result']['ready'] and row['result']['httpStatus'] == 200 for row in restored['semanticHealth'].values())
    assert restored['activeOwnerConfigurationPin'] == source['controllers'][0]['ownerConfigurationPin']
    assert restored['activeCaptureConfigurationPin']
    expected_count = 10044 if kind in ('FULL', 'I2') else 0
    assert restored['failedOriginals'] == dict(inventoryCount=10044, fullShaVerified=expected_count == 10044,
        verifiedFiles=expected_count, mode='FULL_SHA256' if expected_count else 'NOT_RECHECKED_THIS_OBSERVATION')
    assert restored['failedOriginalFilesPreserved'] == expected_count
    assert moment(restored['observedAt']) >= moment(audit['finishedAt'])
    prefix = 'automatic-' + kind.lower()
    installation_name = 'automatic-control-installation-57.json' if installation_pin is None else installation_pin['file']
    if installation_pin is not None:
        assert pinned(task, installation_pin) == source
    names = dict(installation=installation_name, submission=prefix + '-ui-submission.json',
                 audit=prefix + '-audit.json', terminal=prefix + '-ui-terminal.json')
    for key, name in names.items():
        actual = file_pin(task, name)
        assert restored['inputPins'][key] == dict(path=(task / name).resolve().as_posix(), bytes=actual['bytes'], sha256=actual['sha256']), 'SOURCE_RESTORATION_INPUT_CHANGED'


def automatic_chain(task):
    """Cross-bind real UI requests, immutable audit records, and final live plan."""
    selection = read(task, 'automatic-acceptance-selection.json')
    assert selection['schemaVersion'] == 'TaskAutomaticAcceptanceSelection/v2'
    assert set(selection['kinds']) == {'FULL', 'I1', 'I2'}
    operation_ids = []
    commits = {}
    previous = None
    evidence_pins = []
    for index, kind in enumerate(('FULL', 'I1', 'I2')):
        from automatic_stage_deployment import load_stage_deployment
        deployment = load_stage_deployment(task, PRIVATE, kind)
        assert selection['kinds'][kind]['deploymentSelectionPin'] == deployment['selectionPin']
        source = deployment['sourceInstallation']
        validate_source_spug(task, source, deployment['spugInstallation'])
        commits[kind] = source['sourceCommit']
        prefix = 'automatic-' + kind.lower()
        receipt = read(task, prefix + '-ui-submission.json')
        terminal = read(task, prefix + '-ui-terminal.json')
        audit = read(task, prefix + '-audit.json')
        observed = pinned(task, selection['kinds'][kind]['submissionObservationPin'])
        final_ui = pinned(task, selection['kinds'][kind]['terminalObservationPin'])
        restoration_pin = selection['kinds'][kind]['sourceRestorationReportPin']
        assert restoration_pin['file'] == prefix + '-source-restoration.json'
        source_restoration = pinned(task, restoration_pin)
        assert receipt['schemaVersion'] == ('AutomaticIncrementalUiSubmission/v1' if kind == 'FULL' else 'AutomaticIncrementalUiSubmission/v2') and receipt['kind'] == kind
        assert receipt['applicationId'] == SOURCE and receipt['implementationCommit'] == source['sourceCommit']
        if kind != 'FULL':
            assert receipt['deploymentSelectionPin'] == deployment['selectionPin']
            assert receipt['spugCommit'] == deployment['spugCommit']
        request = receipt['request']
        assert request['schemaVersion'] == 'SmallAppBackupUiRequest/v1' and request['sourceConfigRef'] == SOURCE
        assert request['action'] == ('FULL' if index == 0 else 'INCREMENTAL')
        assert request['parentChainRef'] == (None if index == 0 else operation_ids[-1])
        assert request['recoveryPointRef'] is None and request['targetConfigRef'] is None
        operation_ids.append(request['operationId'])
        assert len(set(operation_ids)) == len(operation_ids), 'AUTOMATIC_OPERATION_REUSED'
        plan = receipt['plan']
        assert plan['state'] == ('BASELINE_REQUIRED' if index == 0 else 'READY')
        assert plan['sourceConfigRef'] == SOURCE
        assert plan['parentChainRef'] == request['parentChainRef']
        assert plan['baseFullRef'] == (None if index == 0 else operation_ids[0])
        assert receipt['intent'] == dict(schemaVersion='AutomaticIncrementalRequest/v1', applicationId=SOURCE,
                                       operationId=request['operationId'], planDigest=plan['planDigest'])
        assert observed['schemaVersion'] == final_ui['schemaVersion'] == 'AutomaticIncrementalUiObservation/v1'
        assert observed['phase'] == 'submit' and observed['businessPosts'] == 1
        assert observed['realBrowser'] and observed['identityVerified'] and observed['permissionVerified']
        assert not observed['blockedRequests'] and observed['pageErrorCount'] == 0 and observed['request'] == request
        assert observed['status'] in ('ACCEPTED_FOLLOW_ORIGINAL', 'ORIGINAL_OBSERVED_AFTER_UNKNOWN')
        assert terminal['schemaVersion'] == 'AutomaticIncrementalUiTerminal/v1' and terminal['operationState'] == 'SUCCEEDED'
        assert terminal['request'] == request and terminal['plan'] == plan
        assert final_ui['phase'] == 'verify' and final_ui['businessPosts'] == 0 and final_ui['status'] == 'SUCCEEDED_VERIFIED'
        assert final_ui['request'] == request and final_ui['identityVerified'] and final_ui['permissionVerified']
        assert final_ui['realBrowser'] and not final_ui['blockedRequests'] and final_ui['pageErrorCount'] == 0
        assert audit['schemaVersion'] == 'AutomaticBackupChainAudit/v1' and audit['status'] == 'PASS'
        assert audit['operationId'] == request['operationId'] and audit['sourceConfigRef'] == SOURCE
        assert audit['pointType'] == request['action'] and audit['state'] == 'SUCCEEDED' and audit['actualExitCode'] == 0
        assert audit['sourceRestored'] is True and audit['sourceRestorationPin']
        validate_native_dispatch(audit)
        assert audit['uniqueOwnerOperationVerified'] is True
        assert audit['sourceEpoch']['epochId'] == source['epoch']['epochId']
        assert [row['operationId'] for row in audit['chain']] == operation_ids
        assert [row['pointType'] for row in audit['chain']] == ['FULL'] + ['INCREMENTAL'] * index
        assert audit['chain'][-1]['pointPin'] == audit['pointPin']
        if previous:
            assert audit['chain'][:-1] == previous['chain'], 'AUTOMATIC_PARENT_CHAIN_CHANGED'
            assert audit['sourceEpoch'] == previous['sourceEpoch'], 'AUTOMATIC_PHYSICAL_EPOCH_CHANGED'
            assert moment(receipt['attemptReservedAt']) > moment(previous['finishedAt'])
        assert audit['package']['allInstalledFilesShaVerified'] is True
        assert audit['package']['fileManifestSha256'] == source['fileManifestSha256']
        assert audit['readback']['payloadContentVerified'] is True
        assert audit['readback']['extraFullPayloadReadDispatched'] is False and audit['readback']['serverDurabilityVerified'] is False
        assert moment(final_ui['finishedAt']) >= moment(audit['finishedAt'])
        validate_source_restoration(task, kind, source_restoration, source, request, audit,
                                    deployment['selection']['sourceInstallationPin'])
        previous = audit
        evidence_pins.extend(file_pin(task, prefix + ending) for ending in ('-ui-submission.json', '-ui-terminal.json', '-audit.json', '-source-restoration.json'))
        evidence_pins.append(deployment['selectionPin'])
    actual = pinned(task, selection['finalSourcePreflightPin'])
    assert actual['status'] == 'PASS' and actual['sourceIdle'] is True and actual['workerCount'] == 0
    assert moment(actual['observedAt']) >= moment(previous['finishedAt'])
    assert actual['epochId'] == source['epoch']['epochId']
    assert actual['deploymentSelectionPin'] == deployment['selectionPin']
    assert all(row['result']['ready'] and row['result']['httpStatus'] == 200 for row in actual['health'].values())
    assert actual['plan']['state'] == 'READY' and actual['plan']['sourceConfigRef'] == SOURCE
    assert actual['plan']['parentChainRef'] == operation_ids[-1] and actual['plan']['baseFullRef'] == operation_ids[0]
    return dict(status='PASS', operationIds=dict(zip(('FULL', 'I1', 'I2'), operation_ids)),
                sourceCommit=source['sourceCommit'], operationSourceCommits=commits, finalFinishedAt=previous['finishedAt'],
                finalPlanDigest=actual['plan']['planDigest'], evidencePins=evidence_pins,
                originalBackupEvidenceUnmodified=True, serverDurabilityVerified=False)
