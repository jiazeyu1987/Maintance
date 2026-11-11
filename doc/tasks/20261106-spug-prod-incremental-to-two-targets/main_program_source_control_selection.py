"""Bind a source-only candidate without claiming an installation or runtime proof.

The caller supplies a formally loaded base installation. This adapter checks its
original records again and projects a BOUND candidate; runtime consumers must
continue to reject this schema until an actual activation protocol is provided.
"""
from copy import deepcopy
from pathlib import Path, PurePosixPath
import re

import main_program_control_staging as staging
import main_program_installation_selection as contract
import main_program_spug_publication as publication


SOURCE = 'intruoyi-57-safe-20261024-v1'
CHANGED_FILES = {'control/recovery_control_smallapp.py',
                 'control/recovery_control_smallapp_native.py'}
OVERLAY_FIELDS = {'schemaVersion', 'baseSelectionPin', 'sourceSuccessorReceiptPin'}
RECEIPT_FIELDS = {'schemaVersion', 'status', 'baseSelectionPin',
                  'previousControllerPin', 'currentControllerPin', 'buildPin', 'packageDeltaPin'}
ROW_FIELDS = {'schemaVersion', 'status', 'role', 'host', 'sourceConfigRef',
              'service', 'engine', 'pid', 'sourceCommit', 'buildPin', 'fileCount',
              'fileManifestSha256', 'packageSha256', 'controlConfigurationPin', 'ownerConfigurationPin'}
DELTA_FIELDS = {'schemaVersion', 'status', 'previousBuildPin', 'buildPin',
                'previousPackagePin', 'currentPackagePin', 'changedFiles'}


def need(condition, reason):
    if not condition:
        raise ValueError('SOURCE_SUCCESSOR_' + reason)


def _base(records, base):
    need(type(base) is dict and type(base.get('generation')) is dict, 'BASE_INVALID')
    selected = records.pinned(base['selectionPin'])
    need(selected == base['selection'] and selected.get('schemaVersion') ==
         'TaskMainProgramInstallations/v4', 'BASE_SELECTION_CHANGED')
    generation = records.pinned(selected['controlGenerationPin'])
    projection = base['generation']
    need(projection['generationPin'] == selected['controlGenerationPin'] and
         projection['generation'] == generation and generation['sourceCommit'] ==
         selected['sourceCommit'], 'BASE_GENERATION_CHANGED')
    build = records.pinned(generation['buildPin'])
    need(build == projection['build'] and build['targetCommit'] == selected['sourceCommit'],
         'BASE_BUILD_CHANGED')
    pins = generation['controllersByHost']
    need(type(pins) is dict and set(pins) == set(contract.HOSTS), 'BASE_CONTROLLERS_INVALID')
    rows = {}
    for host, roles in contract.ROLES.items():
        need(type(pins[host]) is list and len(pins[host]) == len(roles), 'BASE_CONTROLLERS_INVALID')
        rows[host] = [records.pinned(reference) for reference in pins[host]]
        need(tuple(row['role'] for row in rows[host]) == roles and
             all(row['host'] == '172.30.30.' + host and row['buildPin'] == generation['buildPin']
                 and row['sourceCommit'] == selected['sourceCommit'] for row in rows[host]),
             'BASE_CONTROLLER_IDENTITY_CHANGED')
    need(rows == projection['controllersByHost'], 'BASE_CONTROLLER_CHANGED')
    for key in ('spugInstallationPin', 'verificationInputsPin'):
        records.pinned(selected[key])
    for reference in base['inputPins']:
        publication.verify_bytes(reference)
    return selected, generation, build, rows


def _candidate_row(row, receipt, previous, build):
    need(set(row) == ROW_FIELDS and row['schemaVersion'] == 'MainProgramSourceControllerBinding/v1'
         and row['status'] == 'BOUND' and row['role'] == 'source' and row['host'] == '172.30.30.57'
         and row['sourceConfigRef'] == SOURCE and row['pid'] is None and
         row['service'] == previous['service'] and row['buildPin'] == receipt['buildPin'],
         'CONTROLLER_INVALID')
    need(type(row['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}', row['sourceCommit'])
         and row['sourceCommit'] == build['targetCommit'] and
         all(type(row[key]) is type(build[key]) and row[key] == build[key]
             for key in ('fileCount', 'fileManifestSha256', 'packageSha256')),
         'CONTROLLER_BUILD_CHANGED')
    engine = PurePosixPath(row['engine'])
    need(engine.is_absolute() and str(engine) == row['engine'] and '..' not in engine.parts and
         engine.parent == PurePosixPath(previous['engine']).parent and row['engine'] != previous['engine'],
         'ENGINE_INVALID')
    for key in ('controlConfigurationPin', 'ownerConfigurationPin'):
        contract.remote_pin(row[key])
        need(row[key]['path'] != previous[key]['path'], 'CONFIGURATION_PATH_REUSED')


def _packages(delta, receipt, generation, original_build, build):
    need(set(delta) == DELTA_FIELDS and delta['schemaVersion'] == 'MainProgramSourceControlPackageDelta/v1'
         and delta['status'] == 'BOUND' and delta['previousBuildPin'] == generation['buildPin']
         and delta['buildPin'] == receipt['buildPin'], 'PACKAGE_DELTA_BINDING')
    original_pin = original_build['variants']['standard']['packagePin']
    candidate_pin = build['variants']['standard']['packagePin']
    need(delta['previousPackagePin'] == original_pin and delta['currentPackagePin'] == candidate_pin,
         'PACKAGE_DELTA_PINS')
    originals = publication.verify_bytes(original_pin)
    candidates = publication.verify_bytes(candidate_pin)
    before = staging.verify_package(originals, original_build)['payloadFiles']
    after = staging.verify_package(candidates, build)['payloadFiles']
    need(set(before) == set(after) and {name for name in before if before[name] != after[name]} ==
         CHANGED_FILES and type(delta['changedFiles']) is list and
         len(delta['changedFiles']) == len(CHANGED_FILES) and set(delta['changedFiles']) == CHANGED_FILES,
         'PACKAGE_DELTA_CHANGED')
    return original_pin, candidate_pin


def bind_source_successor(base, *, task, selection_file):
    """Return an uninstalled candidate while retaining the original proof objects."""
    records = contract.Records(task)
    overlay = records.read(selection_file)
    need(set(overlay) == OVERLAY_FIELDS and
         overlay['schemaVersion'] == 'TaskMainProgramSourceControlSelection/v1', 'SELECTION_INVALID')
    selected, generation, original_build, rows = _base(records, base)
    need(overlay['baseSelectionPin'] == base['selectionPin'], 'BASE_PIN_CHANGED')
    receipt = records.pinned(overlay['sourceSuccessorReceiptPin'])
    need(set(receipt) == RECEIPT_FIELDS and receipt['schemaVersion'] ==
         'MainProgramSourceControlSuccessorBinding/v1' and receipt['status'] == 'BOUND' and
         receipt['baseSelectionPin'] == base['selectionPin'] and
         receipt['previousControllerPin'] == generation['controllersByHost']['57'][0], 'RECEIPT_INVALID')
    row = records.pinned(receipt['currentControllerPin'])
    build = records.pinned(receipt['buildPin'])
    _candidate_row(row, receipt, rows['57'][0], build)
    packages = _packages(records.pinned(receipt['packageDeltaPin']), receipt, generation, original_build, build)
    effective = deepcopy(rows)
    effective['57'][0] = deepcopy(row)
    bindings = {host: {item['role']: dict(buildPin=deepcopy(item['buildPin']),
        sourceCommit=item['sourceCommit']) for item in items} for host, items in effective.items()}
    result = dict(status='BOUND', installationVerified=False, runtimeVerified=False,
        baseInstallation=deepcopy(base), effectiveControllersByHost=effective,
        controllerBuildBindings=bindings, sourceSuccessorReceiptPin=deepcopy(overlay['sourceSuccessorReceiptPin']))
    # Detect changes after the complete package read, without rewriting any record.
    for reference in records.path_pins() + base['inputPins'] + list(packages):
        publication.verify_bytes(reference)
    return result
