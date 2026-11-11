"""Explicit activated-source overlay; historical proof is never live health.

The original v4 loader retains responsibility for the complete base installation.
This protocol checks every actual source-only activation against that base and
projects per-role identities. It never modifies old selectors or task receipts.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

import main_program_control_activation as activation
import main_program_control_staging as staging
import main_program_current_installation as current
import main_program_installation_selection as contract
import main_program_source_control_selection as bound
import main_program_source_control_successor as successor
import main_program_spug_publication as publication


TASK = Path(__file__).resolve().parent
SCHEMA = 'TaskMainProgramSourceControlSelection/v2'
FIELDS = {'schemaVersion', 'baseSelectionPin', 'activationEvidencePins'}
PROOF_FIELDS = {'activationReceiptPin', 'after', 'authenticatedProbe', 'backupDispatched',
    'baseSelectionPin', 'before', 'buildPin', 'businessContainersRestarted', 'createdPins',
    'currentController', 'host', 'observedAt', 'originalI1QueryCount', 'originalI1Unregistered',
    'originalSourcePins', 'physicalSourceLockHeld', 'previousController', 'previousControllerPin',
    'restoreDispatched', 'schemaVersion', 'serverFilesWritten', 'sourceEpoch', 'status',
    'targetControlReloaded'}
OBS_FIELDS = {'containers', 'controllers', 'fstab', 'historyGuard', 'mountinfoSha256', 'packages'}


def need(condition, reason):
    if not condition:
        raise ValueError('ACTIVATED_SOURCE_' + reason)


def byte_pin(path, raw):
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def unique_pins(pins):
    result = {}
    for pin in pins:
        key = Path(pin['path']).resolve(strict=True)
        need(key not in result or result[key]['bytes'] == pin['bytes'] and
             result[key]['sha256'] == pin['sha256'], 'INPUT_PIN_CONFLICT')
        if key not in result:
            result[key] = pin
    return list(result.values())


def _package(build, pins):
    reference = build['variants']['standard']['packagePin']
    raw = publication.verify_bytes(reference)
    pins.append(reference)
    return raw, staging.verify_package(raw, build)


def _receipt(proof):
    need(type(proof) is dict, 'RECEIPT_INVALID')
    ordinary = set(proof) == PROOF_FIELDS | {'sourceControlReloaded'}
    finalizer = set(proof) == PROOF_FIELDS | {'phase', 'dependencyComparison',
        'sourceControlReloadedPreviously', 'sourceControlReloadedThisPhase'}
    need(ordinary or finalizer, 'RECEIPT_FIELDS')
    if ordinary:
        need(proof['sourceControlReloaded'] is True, 'SOURCE_NOT_RELOADED')
    else:
        need(proof['phase'] == 'VERIFY_ALREADY_ACTIVATED' and
             proof['sourceControlReloadedPreviously'] is True and
             proof['sourceControlReloadedThisPhase'] is False and
             proof['dependencyComparison'] ==
             'After/Requires unique sets; all other process/properties fields exact', 'FINALIZER_INVALID')
    need(proof['schemaVersion'] == 'MainProgramSourceControlActivation/v1' and
         proof['status'] == 'PASS' and proof['host'] == '172.30.30.57' and
         proof['serverFilesWritten'] is True and proof['physicalSourceLockHeld'] is True and
         proof['originalI1Unregistered'] is True and type(proof['originalI1QueryCount']) is int and
         proof['originalI1QueryCount'] == 0 and all(proof[key] is False for key in
         ('backupDispatched', 'restoreDispatched', 'targetControlReloaded', 'businessContainersRestarted')),
         'RECEIPT_SCOPE')
    reference = contract.remote_pin(proof['activationReceiptPin'])
    raw = publication.canonical({key: value for key, value in proof.items() if key != 'activationReceiptPin'})
    need(byte_pin(reference['path'], raw) == reference, 'RECEIPT_BYTES')
    need(proof['authenticatedProbe'] == dict(status=404, errorCode='TRANSPORT_ROUTE_UNKNOWN',
         operationRead=False, planRead=False), 'AUTHENTICATED_PROBE')


def _observations(proof, old, row, old_package, new_package, control, last_after):
    before, after = proof['before'], proof['after']
    need(type(before) is dict and type(after) is dict and
         set(before) == set(after) == OBS_FIELDS, 'OBSERVATION_FIELDS')
    need(all(before[key] == after[key] for key in ('containers', 'fstab', 'mountinfoSha256')) and
         bool(before['containers']) and contract.sha(before['mountinfoSha256']) and
         successor.systemd_properties_equal(before['historyGuard'], after['historyGuard']), 'BUSINESS_CHANGED')
    a, b = before['controllers'], after['controllers']
    need(type(a) is list and type(b) is list and len(a) == len(b) == 2 and
         successor.process_observation_equal(a[1], b[1]), 'TARGET_CHANGED')
    if last_after is not None:
        need(all(successor.process_observation_equal(x, y) for x, y in
             zip(last_after['controllers'], a)), 'PROCESS_CONTINUITY')
    for observed, expected in ((a[0], old), (b[0], row)):
        need(observed['service'] == expected['service'] and observed['pid'] == expected['pid'] and
             observed['properties']['MainPID'] == str(expected['pid']) and
             observed['properties']['ActiveState'] == 'active' and
             observed['properties']['SubState'] == 'running' and
             observed['properties']['LimitNOFILE'] == '65536', 'SOURCE_PROCESS')
    old_props, props = deepcopy(a[0]['properties']), deepcopy(b[0]['properties'])
    old_props['MainPID'] = props['MainPID']
    old_props['DropInPaths'] += ' ' + row['dropinPin']['path']
    need(successor.systemd_properties_equal(old_props, props), 'SOURCE_UNIT_CHANGED')
    args = [control['pythonPin']['path'], '-B', row['engine'] + '/control_entry.py', 'serve',
            '--config-pin', publication.canonical(row['controlConfigurationPin']).decode('utf-8')]
    need(b[0]['argvSha256'] == hashlib.sha256(('\0'.join(args) + '\0').encode('utf-8')).hexdigest() and
         b[0]['environmentVerification']['mode'] == 'CONFIG_EXACT' and
         contract.sha(b[0]['environmentVerification']['environmentSha256']) and
         a[0]['executable'] == b[0]['executable'], 'SOURCE_ARGV_CHANGED')
    old_pin = byte_pin(PurePosixPath(old['engine']) / 'package.json', old_package['files']['package.json'])
    new_pin = byte_pin(PurePosixPath(row['engine']) / 'package.json', new_package['files']['package.json'])
    need(type(before['packages']) is list and len(before['packages']) == 2 and
         after['packages'] == [new_pin, before['packages'][1]] and
         before['packages'][0] == old_pin, 'PACKAGE_OBSERVATION')


def verify_source_activations(base, steps, *, task=TASK):
    """Pure local proof projection; caller must formally load the base first."""
    need(type(steps) is list and 0 < len(steps) <= 16, 'ACTIVATIONS_REQUIRED')
    rows = deepcopy(base['generation']['controllersByHost'])
    previous = deepcopy(base['generation']['selections']['57']['controllers'][0])
    need(all(key in rows['57'][0] and rows['57'][0][key] == value
             for key, value in previous.items()), 'BASE_SOURCE_PROJECTION')
    previous_pin = base['generation']['generation']['controllersByHost']['57'][0]
    previous_build = base['generation']['build']
    documents = base['generation']['privatePlan']['documentsByHost']['57']
    def original(key):
        matches = [item for item in documents if item['pin'] == previous[key]]
        need(len(matches) == 1, 'BASE_CONFIGURATION_MISSING')
        return deepcopy(matches[0]['value'])
    control, owner = original('controlConfigurationPin'), original('ownerConfigurationPin')
    pins = []
    old_raw, old_package = _package(previous_build, pins)
    epoch, last_after = None, None
    records = contract.Records(task)
    for step in steps:
        need(type(step) is dict and set(step) == {'proof', 'build'}, 'STEP_FIELDS')
        proof, build = step['proof'], step['build']
        _receipt(proof)
        need(proof['baseSelectionPin'] == base['selectionPin'] and
             proof['previousController'] == previous and
             proof['previousControllerPin'] == previous_pin, 'CONTINUITY')
        need(records.pinned(proof['buildPin']) == build, 'BUILD_CHANGED')
        raw, package = _package(build, pins)
        changed = {name for name in old_package['payloadFiles'] if
                   old_package['payloadFiles'][name] != package['payloadFiles'].get(name)}
        candidate = successor.prepare_candidate(previous=previous, control=control, owner=owner,
            previous_build=previous_build, build=build, previous_package_raw=old_raw,
            package_raw=raw, expected_changed_files=changed)
        row = proof['currentController']
        need(type(row) is dict and type(row.get('pid')) is int and row['pid'] > 0 and
             row.get('schemaVersion') in ('MainProgramSourceController/v1',
                                         'MainProgramSourceControllerBinding/v1'), 'CONTROLLER')
        expected = dict(candidate['controller'], schemaVersion=row['schemaVersion'],
            status='PASS', pid=row['pid'], buildPin=proof['buildPin'])
        existing = [PurePosixPath(path).name for path in
                    proof['before']['controllers'][0]['properties']['DropInPaths'].split()]
        name, dropin = activation.make_dropin(previous['service'], expected['engine'],
            expected['controlConfigurationPin'], candidate['control'], existing,
            build['targetCommit'], 'spug-history-prod57-readonly-57.service')
        expected['dropinPin'] = byte_pin('/etc/systemd/system/' + previous['service'] + '.d/' + name, dropin)
        need(row == expected, 'CONTROLLER_CHANGED')
        receipt_path = str(PurePosixPath(expected['controlConfigurationPin']['path']).parent / 'activation-source.json')
        need(proof['activationReceiptPin']['path'] == receipt_path, 'RECEIPT_PATH')
        created = [byte_pin(PurePosixPath(row['engine']) / name, content)
                   for name, content in sorted(candidate['files'].items())]
        created += [row['ownerConfigurationPin'], row['controlConfigurationPin'], row['dropinPin']]
        need(proof['createdPins'] == created and
             proof['originalSourcePins'][-2:] == [previous['controlConfigurationPin'], previous['ownerConfigurationPin']],
             'CREATED_OR_ORIGINAL_PINS')
        observed_epoch = proof['sourceEpoch']
        need(type(observed_epoch) is dict and observed_epoch.get('schemaVersion') == 'SourceBackupEpoch/v1' and
             observed_epoch.get('state') == 'READY' and observed_epoch.get('operationId') is None and
             contract.sha(observed_epoch.get('epochId')) and
             (epoch is None or epoch == observed_epoch), 'EPOCH_CHANGED')
        _observations(proof, previous, row, old_package, package, candidate['control'], last_after)
        target = rows['57'][1]
        need(proof['after']['controllers'][1]['service'] == target['service'] and
             proof['after']['controllers'][1]['pid'] == target['pid'], 'BASE_TARGET_CHANGED')
        epoch, last_after = observed_epoch, proof['after']
        previous, previous_pin = deepcopy(row), proof['activationReceiptPin']
        control, owner = candidate['control'], candidate['owner']
        previous_build, old_raw, old_package = build, raw, package
    rows['57'][0] = previous
    for pin in pins + records.path_pins():
        publication.verify_bytes(pin)
    bindings = {host: {row['role']: dict(buildPin=deepcopy(row['buildPin']), sourceCommit=row['sourceCommit'])
                      for row in values} for host, values in rows.items()}
    return dict(status='ACTIVATED', installationVerified=True, runtimeVerified=False,
        baseInstallation=deepcopy(base), effectiveControllersByHost=rows, controllerBuildBindings=bindings,
        sourceControl=control, sourceOwner=owner, sourceEpoch=deepcopy(epoch),
        activationReceiptPins=[deepcopy(step['proof']['activationReceiptPin']) for step in steps],
        inputPins=pins + records.path_pins())


def load_activated_installation(task, private, *, selection_file, historical_source_custody_pin=None):
    code_pins = [publication.file_pin(Path(module.__file__).resolve()) for module in
                 (activation, staging, current, contract, bound, successor, publication)]
    code_pins.append(publication.file_pin(Path(__file__).resolve()))
    records = contract.Records(task)
    overlay = records.read(selection_file)
    need(set(overlay) == FIELDS and overlay['schemaVersion'] == SCHEMA, 'SELECTION')
    base_reference = overlay['baseSelectionPin']
    records.pinned(base_reference)
    args = {} if historical_source_custody_pin is None else dict(
        historical_source_custody_pin=historical_source_custody_pin)
    base = current.load_current_installation(task, private,
        selection_file=base_reference['file'], **args)
    bound._base(records, base)
    need(base['selectionPin'] == base_reference and type(overlay['activationEvidencePins']) is list and
         0 < len(overlay['activationEvidencePins']) <= 16, 'SELECTION_BINDING')
    pins, steps = [], []
    for reference in overlay['activationEvidencePins']:
        need(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'}, 'EVIDENCE_PIN')
        raw = publication.verify_bytes(reference)
        proof = json.loads(raw.decode('utf-8'), object_pairs_hook=contract.document)
        build = records.pinned(proof['buildPin'])
        pins.append(reference)
        steps.append(dict(proof=proof, build=build))
    result = verify_source_activations(base, steps, task=task)
    result.update(selection=overlay, selectionPin=records.references[selection_file])
    result['inputPins'] += records.path_pins() + base['inputPins'] + pins + code_pins
    result['inputPins'] = unique_pins(result['inputPins'])
    for reference in result['inputPins']:
        publication.verify_bytes(reference)
    return result


def public_summary(result):
    base = result['baseInstallation']
    row = result['effectiveControllersByHost']['57'][0]
    return dict(schemaVersion='MainProgramSourceInstallationSummary/v1', status='PASS',
        selectionPin=result['selectionPin'], baseSelectionPin=base['selectionPin'],
        sourceCommit=row['sourceCommit'], baseSourceCommit=base['selection']['sourceCommit'],
        controlGenerationPin=base['selection']['controlGenerationPin'],
        spugInstallationPin=base['selection']['spugInstallationPin'], buildPin=row['buildPin'],
        baseBuildPin=base['generation']['generation']['buildPin'],
        build={key: row[key] for key in ('fileCount', 'fileManifestSha256', 'packageSha256')},
        controllerBuildBindings=result['controllerBuildBindings'],
        resourceBuildPin=base['spugRuntime']['resourceBuildPin'],
        spugCommit=base['spugRuntime']['resourceBuild']['sourceCommit'],
        installationVerified=True, runtimeVerified=False, inputPins=result['inputPins'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', required=True)
    parser.add_argument('--historical-source-custody')
    parser.add_argument('--public-summary', action='store_true', required=True)
    args = parser.parse_args()
    try:
        custody = None if args.historical_source_custody is None else publication.file_pin(
            Path(args.historical_source_custody))
        result = load_activated_installation(TASK, publication.PRIVATE,
            selection_file=args.selection, historical_source_custody_pin=custody)
        print(json.dumps(public_summary(result), ensure_ascii=False))
    except Exception:
        print('ACTIVATED_SOURCE_INSTALLATION_VALIDATION_FAILED', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
