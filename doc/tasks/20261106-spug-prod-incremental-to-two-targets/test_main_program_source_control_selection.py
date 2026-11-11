"""File-based BOUND projection, using original r7 records; no server simulation."""
from copy import deepcopy
import hashlib
import importlib
import io
import json
from pathlib import Path
import tarfile

import pytest

import main_program_current_installation as current
import main_program_installation_selection as contract
import main_program_spug_publication as publication


TASK = Path(__file__).resolve().parent
SELECTION = 'main-program-current-installations-b5fa4c5-r7-v4.json'
SOURCE = 'intruoyi-57-safe-20261024-v1'
CHANGED = ['control/recovery_control_smallapp.py', 'control/recovery_control_smallapp_native.py']
COMMIT = 'c' * 40


def subject():
    return importlib.import_module('main_program_source_control_selection')


def put(root, name, value):
    path = root / name
    path.write_bytes(publication.canonical(value))
    pin = publication.file_pin(path)
    return dict(file=name, bytes=pin['bytes'], sha256=pin['sha256'])


def copy_record(root, reference):
    path = root / reference['file']
    path.write_bytes((TASK / reference['file']).read_bytes())
    assert publication.file_pin(path)['sha256'] == reference['sha256']
    return json.loads(path.read_bytes())


@pytest.fixture(scope='module')
def original_package():
    build = json.loads((TASK / 'release-build-b5fa4c5.json').read_bytes())
    pin = build['variants']['standard']['packagePin']
    raw = publication.verify_bytes(pin)
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        files = {member.name: archive.extractfile(member).read() for member in archive.getmembers()}
    return build, pin, files


def candidate_package(root, original, extra=False):
    build, _, files = original
    files = deepcopy(files)
    for name in CHANGED + (['control_entry.py'] if extra else []):
        assert name in files
        files[name] += b'\n# BOUND unit candidate; never installed.\n'
    metadata = json.loads(files['package.json'])
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items() if name != 'package.json'}
    metadata.update(files=hashes, packageSha256=hashlib.sha256(publication.canonical(hashes)).hexdigest())
    files['package.json'] = publication.canonical(metadata)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, raw in files.items():
            member = tarfile.TarInfo(name); member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
    path = root / 'candidate-standard.tgz'; path.write_bytes(stream.getvalue())
    pin = publication.file_pin(path)
    value = deepcopy(build)
    value.update(targetCommit=COMMIT, packageSha256=pin['sha256'], fileManifestSha256=metadata['packageSha256'])
    value['variants']['standard'].update(packagePin=pin, fileManifestSha256=metadata['packageSha256'])
    return value, pin


@pytest.fixture
def records(tmp_path, original_package):
    original = contract.Records(TASK); selected = original.read(SELECTION)
    selection_pin = original.references[SELECTION]
    copy_record(tmp_path, selection_pin)
    generation = copy_record(tmp_path, selected['controlGenerationPin'])
    build = copy_record(tmp_path, generation['buildPin'])
    for key in ('spugInstallationPin', 'verificationInputsPin'):
        copy_record(tmp_path, selected[key])
    rows = {host: [copy_record(tmp_path, pin) for pin in pins]
            for host, pins in generation['controllersByHost'].items()}
    assert [row['role'] for row in rows['57']] == ['source', 'target']
    assert len(rows['58']) == len(rows['59']) == 1
    # This is only the public-record projection supplied to a pure binder.
    # It is deliberately not a fabricated completed acceptance or runtime proof.
    base = dict(selection=selected, selectionPin=selection_pin,
        generation=dict(generationPin=selected['controlGenerationPin'], generation=generation,
                        build=build, controllersByHost=rows),
        spugRuntime=dict(opaqueOriginalInstallationPin=selected['spugInstallationPin']),
        inputPins=[publication.file_pin(path) for path in tmp_path.glob('*.json')])
    new_build, package_pin = candidate_package(tmp_path, original_package)
    build_pin = put(tmp_path, 'candidate-build.json', new_build)
    before = rows['57'][0]
    engine = str(Path(before['engine']).as_posix()).replace('engine-main-program-b5fa4c5', 'engine-source-control-ccccccc')
    row = dict(schemaVersion='MainProgramSourceControllerBinding/v1', status='BOUND', role='source',
        host='172.30.30.57', sourceConfigRef=SOURCE, service=before['service'], engine=engine,
        pid=None, sourceCommit=COMMIT, buildPin=build_pin,
        **{key: new_build[key] for key in ('fileCount', 'fileManifestSha256', 'packageSha256')},
        controlConfigurationPin=deepcopy(before['controlConfigurationPin']),
        ownerConfigurationPin=deepcopy(before['ownerConfigurationPin']))
    for key in ('controlConfigurationPin', 'ownerConfigurationPin'):
        row[key]['path'] = row[key]['path'].replace('main-program-b5fa4c5-r7', 'source-control-ccccccc')
        row[key]['sha256'] = 'd' * 64
    row_pin = put(tmp_path, 'candidate-controller.json', row)
    delta = dict(schemaVersion='MainProgramSourceControlPackageDelta/v1', status='BOUND',
        previousBuildPin=generation['buildPin'], buildPin=build_pin,
        previousPackagePin=original_package[1], currentPackagePin=package_pin, changedFiles=CHANGED)
    delta_pin = put(tmp_path, 'candidate-delta.json', delta)
    receipt = dict(schemaVersion='MainProgramSourceControlSuccessorBinding/v1', status='BOUND',
        baseSelectionPin=selection_pin, previousControllerPin=generation['controllersByHost']['57'][0],
        currentControllerPin=row_pin, buildPin=build_pin, packageDeltaPin=delta_pin)
    receipt_pin = put(tmp_path, 'candidate-receipt.json', receipt)
    overlay = dict(schemaVersion='TaskMainProgramSourceControlSelection/v1', baseSelectionPin=selection_pin,
                   sourceSuccessorReceiptPin=receipt_pin)
    put(tmp_path, 'bound-selection.json', overlay)
    return dict(root=tmp_path, base=base, row=row, receipt=receipt, delta=delta, overlay=overlay,
                build=new_build, original=original_package)


def bind(data):
    return subject().bind_source_successor(data['base'], task=data['root'], selection_file='bound-selection.json')


def repin(data, kind):
    if kind == 'row':
        data['receipt']['currentControllerPin'] = put(data['root'], 'candidate-controller.json', data['row'])
    if kind == 'delta':
        data['receipt']['packageDeltaPin'] = put(data['root'], 'candidate-delta.json', data['delta'])
    data['overlay']['sourceSuccessorReceiptPin'] = put(data['root'], 'candidate-receipt.json', data['receipt'])
    put(data['root'], 'bound-selection.json', data['overlay'])


def test_bound_replaces_only_source_with_its_own_build_and_preserves_original_files(records):
    before = deepcopy(records['base'])
    pins_before = {str(path): publication.file_pin(path) for path in records['root'].iterdir()}
    old_i1 = publication.verify_bytes(publication.file_pin(TASK / 'automatic-main-r7-20261110-i1-ui-submission.json'))
    result = bind(records)
    assert result['status'] == 'BOUND'
    assert result['installationVerified'] is result['runtimeVerified'] is False
    assert result['baseInstallation'] == before == records['base']
    effective = result['effectiveControllersByHost']
    assert effective['57'][0] == records['row'] and effective['57'][0]['pid'] is None
    assert effective['57'][1:] == before['generation']['controllersByHost']['57'][1:]
    assert effective['58'] == before['generation']['controllersByHost']['58']
    assert effective['59'] == before['generation']['controllersByHost']['59']
    bindings = result['controllerBuildBindings']
    assert bindings['57']['source']['buildPin'] == records['receipt']['buildPin']
    assert bindings['57']['source']['sourceCommit'] == COMMIT != before['selection']['sourceCommit']
    for host in ('57', '58', '59'):
        assert bindings[host]['target']['buildPin'] == before['generation']['generation']['buildPin']
        assert bindings[host]['target']['sourceCommit'] == before['selection']['sourceCommit']
    assert result['baseInstallation']['spugRuntime'] == before['spugRuntime']
    assert {path: publication.file_pin(Path(path)) for path in pins_before} == pins_before
    assert (TASK / 'automatic-main-r7-20261110-i1-ui-submission.json').read_bytes() == old_i1


@pytest.mark.parametrize('change', ['status', 'extra', 'wrong-base', 'wrong-previous', 'role', 'source', 'pid'])
def test_invalid_receipt_or_source_identity_never_binds(records, change):
    if change == 'status': records['receipt']['status'] = 'ACTIVATED'
    elif change == 'extra': records['receipt']['allowOtherTargets'] = True
    elif change == 'wrong-base': records['receipt']['baseSelectionPin']['sha256'] = '0' * 64
    elif change == 'wrong-previous': records['receipt']['previousControllerPin'] = records['base']['generation']['generation']['controllersByHost']['57'][1]
    elif change == 'role': records['row']['role'] = 'target'
    elif change == 'source': records['row']['sourceConfigRef'] = 'another-source'
    else: records['row']['pid'] = 12345
    repin(records, 'row' if change in ('role', 'source', 'pid') else 'receipt')
    with pytest.raises(ValueError): bind(records)


def test_extra_actual_package_delta_is_rejected_even_when_declared_list_hides_it(records):
    build, package_pin = candidate_package(records['root'], records['original'], extra=True)
    build_pin = put(records['root'], 'candidate-build.json', build)
    records['receipt']['buildPin'] = build_pin
    records['row']['buildPin'] = build_pin
    records['row'].update({key: build[key] for key in ('fileManifestSha256', 'packageSha256')})
    records['delta'].update(buildPin=build_pin, currentPackagePin=package_pin)
    repin(records, 'row'); repin(records, 'delta')
    with pytest.raises(ValueError, match='SOURCE_SUCCESSOR_PACKAGE_DELTA'):
        bind(records)


def test_original_base_controller_drift_cannot_be_hidden_by_receipt(records):
    records['base']['generation']['controllersByHost']['58'][0]['pid'] += 1
    with pytest.raises(ValueError, match='SOURCE_SUCCESSOR_BASE'):
        bind(records)


def test_bound_overlay_never_enters_current_installation_or_selector(records):
    bind(records)
    with pytest.raises(ValueError, match='CURRENT_INSTALLATION_SELECTION'):
        current.load_current_installation(records['root'], records['root'], selection_file='bound-selection.json')
    with pytest.raises(ValueError):
        contract.select_main_program_installation('57', records['root'], selection_file='bound-selection.json')
