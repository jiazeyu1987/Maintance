"""Local original-evidence and projection contracts, never an r7 activation fixture."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import main_program_installation_selection as contract
import main_program_spug_publication as publication
import main_program_spug_publication_verify_only as legacy
import main_program_spug_control_generation_acceptance as acceptance
from test_main_program_spug_control_generation_acceptance import actual, TASK, PRIVATE

OLD_SELECTION = 'main-program-current-installations-45dd7dc-r6-v4.json'
NEW_SCHEMA = 'MainProgramSpugControlGenerationAcceptanceInputs/v1'


def subject():
    return importlib.import_module('main_program_current_installation')


def put(root, name, value):
    path = root/name
    path.write_bytes(publication.canonical(value))
    pin = publication.file_pin(path)
    return dict(file=name, bytes=pin['bytes'], sha256=pin['sha256'])


def selector(root, schema):
    inputs = put(root, 'inputs.json', dict(schemaVersion=schema))
    generation = put(root, 'generation.json', {})
    result = put(root, 'result.json', {})
    selected = dict(schemaVersion='TaskMainProgramInstallations/v4', sourceCommit='a'*40,
                    controlGenerationPin=generation, spugInstallationPin=result, verificationInputsPin=inputs)
    put(root, 'selection.json', selected)
    return selected


@pytest.mark.parametrize('schema', ['Unknown/v1', '', None])
def test_unknown_inputs_never_select_a_fallback(tmp_path, monkeypatch, schema):
    selector(tmp_path, schema)
    def forbidden(*args, **kwargs):
        pytest.fail('unrecognized schema called a completed validator')
    monkeypatch.setattr(legacy, 'validate_publication_v4', forbidden)
    monkeypatch.setattr(acceptance, 'load_completed_acceptance', forbidden)
    with pytest.raises(ValueError, match='CURRENT_INSTALLATION_INPUT_SCHEMA'):
        subject().load_current_installation(tmp_path, tmp_path, selection_file='selection.json')


@pytest.mark.parametrize('change', ['extra', 'missing', 'v3', 'commit'])
def test_exact_original_five_fields_required_before_any_loader(tmp_path, change):
    selected = selector(tmp_path, NEW_SCHEMA)
    if change == 'extra': selected['implicitLatest'] = True
    elif change == 'missing': del selected['verificationInputsPin']
    elif change == 'v3': selected['schemaVersion'] = 'TaskMainProgramInstallations/v3'
    else: selected['sourceCommit'] = 'bad'
    put(tmp_path, 'selection.json', selected)
    with pytest.raises(ValueError, match='CURRENT_INSTALLATION_SELECTION'):
        subject().load_current_installation(tmp_path, tmp_path, selection_file='selection.json')


@pytest.mark.parametrize('schema', [legacy.INPUT_SCHEMA, 'MainProgramSpugPublicationVerificationInputs/v2', NEW_SCHEMA])
def test_dispatch_calls_only_the_exact_formal_loader_and_propagates_failure(tmp_path, monkeypatch, schema):
    selected = selector(tmp_path, schema)
    called = []
    def old(records, private, value):
        called.append('old')
        assert value == selected
        raise RuntimeError('ORIGINAL_VALIDATOR_SENTINEL')
    def new(task, private, pin):
        called.append('new')
        assert pin == selected['spugInstallationPin']
        raise RuntimeError('ORIGINAL_VALIDATOR_SENTINEL')
    monkeypatch.setattr(legacy, 'validate_publication_v4', old)
    monkeypatch.setattr(acceptance, 'load_completed_acceptance', new)
    with pytest.raises(RuntimeError, match='ORIGINAL_VALIDATOR_SENTINEL'):
        subject().load_current_installation(tmp_path, tmp_path, selection_file='selection.json')
    assert called == (['new'] if schema == NEW_SCHEMA else ['old'])


def test_real_old_selector_keeps_exact_original_failure_or_success():
    module = subject()
    records = contract.Records(TASK)
    selected = records.read(OLD_SELECTION)
    try:
        original = legacy.validate_publication_v4(records, PRIVATE, selected)
    except (ValueError, OSError) as error:
        with pytest.raises(type(error)) as observed:
            module.load_current_installation(TASK, PRIVATE, selection_file=OLD_SELECTION)
        assert str(observed.value) == str(error)
    else:
        current = module.load_current_installation(TASK, PRIVATE, selection_file=OLD_SELECTION)
        assert current['generation'] == original['generation']


def test_thin_pass_acceptance_cannot_replace_original_native_closure(tmp_path):
    selected = selector(tmp_path, NEW_SCHEMA)
    selected['spugInstallationPin'] = put(tmp_path, 'result.json', dict(
        schemaVersion=acceptance.SCHEMA, recordType='result', status='PASS',
        acceptanceInputsPin=selected['verificationInputsPin']))
    put(tmp_path, 'selection.json', selected)
    with pytest.raises((ValueError, KeyError)):
        subject().load_current_installation(tmp_path, tmp_path, selection_file='selection.json')


def test_actual_history_resource_projection_uses_transition_inputs_565(actual):
    # Pure projection of real verified old history, not a new completed result.
    reader = subject().BoundDocuments(TASK, actual['verified']['inputPins']+[actual['custody']])
    inputs = dict(schemaVersion=NEW_SCHEMA, historicalReadCustodyPin=actual['custody'])
    reference = subject().resource_build_reference(reader, inputs)
    value = reader.read(reference)
    assert reference['file'] == 'spug-resource-build-5651efc-r3.json'
    assert value['sourceCommit'] == '5651efc5b9972b20bcacb50d0774e5862cbe8e6b'
    reader.finish()


def test_actual_old_projection_preserves_seven_original_published_paths(actual):
    reader = subject().BoundDocuments(TASK, actual['verified']['inputPins']+[actual['custody']])
    inputs = dict(schemaVersion=NEW_SCHEMA, historicalReadCustodyPin=actual['custody'])
    pins = subject().published_configuration_pins(reader, inputs)
    assert len(pins) == 7
    expected = [dict(path=row['path'], bytes=len(publication.canonical(row['value'])),
        sha256=__import__('hashlib').sha256(publication.canonical(row['value'])).hexdigest())
        for row in actual['base']['spec']['spugSpec']['writes']]
    assert sorted(pins,key=lambda p:p['path']) == sorted(expected,key=lambda p:p['path'])
    assert not any(Path(pin['path']).name in actual['secret']['newConnections'] for pin in pins)


@pytest.mark.parametrize('change', ['outside', 'bytes', 'sha', 'path'])
def test_bound_documents_reject_unbound_or_changed_pin(tmp_path, change):
    reference = put(tmp_path, 'original.json', dict(value='bound'))
    full = publication.file_pin(tmp_path/reference['file'])
    reader = subject().BoundDocuments(tmp_path, [full])
    expected = dict(reference)
    if change == 'outside': expected = put(tmp_path, 'other.json', dict(value='not bound'))
    elif change == 'path': expected['file'] = '../original.json'
    elif change == 'bytes': expected['bytes'] += 1
    else: expected['sha256'] = '0'*64
    with pytest.raises(ValueError): reader.read(expected)


def test_bound_documents_reread_all_originals_on_finish(tmp_path):
    reference = put(tmp_path, 'original.json', dict(value='bound'))
    reader = subject().BoundDocuments(tmp_path, [publication.file_pin(tmp_path/reference['file'])])
    reader.read(reference)
    (tmp_path/reference['file']).write_bytes(b'{}')
    with pytest.raises(ValueError): reader.finish()


def test_new_build_uses_exact_formal_archive_path_not_commit_directory():
    build = json.loads((TASK/'release-build-b5fa4c5.json').read_bytes())
    reference = subject().standard_package_pin(build, PRIVATE)
    assert reference == build['variants']['standard']['packagePin']
    assert Path(reference['path']).parent.name == 'package-chain-policy-b5fa4c5-20261110-r1'


def test_old_build_resolves_its_registered_output_directory():
    build = json.loads((TASK/'release-build-45dd7dc.json').read_bytes())
    reference = subject().standard_package_pin(build, PRIVATE)
    assert Path(reference['path']).parent == Path(build['buildCommand'][-1])
    assert reference['sha256'] == build['packageSha256']


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'outside', 'hash'])
def test_registered_archive_path_contract_is_not_a_fallback(change):
    build = json.loads((TASK/'release-build-b5fa4c5.json').read_bytes())
    if change == 'missing': del build['buildCommand']
    elif change == 'duplicate': build['buildCommand'] += ['--output-directory', build['buildCommand'][-1]]
    elif change == 'outside': build['buildCommand'][-1] = str(TASK)
    else: build['variants']['standard']['packagePin']['sha256'] = '0'*64
    with pytest.raises(ValueError): subject().standard_package_pin(build, PRIVATE)


def test_safe_summary_contains_pins_and_public_build_identity_only(actual):
    module = subject()
    verified = actual['verified']
    records = contract.Records(TASK)
    selected = records.read(OLD_SELECTION)
    reader = module.BoundDocuments(TASK, verified['inputPins'])
    inputs = reader.read(selected['verificationInputsPin'])
    runtime = module.project_runtime(reader, PRIVATE, selected, inputs, 'PUBLICATION_VERIFICATION')
    current = dict(selection=selected, selectionPin=records.references[OLD_SELECTION],
                   generation=verified['generation'], inputPins=verified['inputPins'], spugRuntime=runtime)
    public = module.public_summary(current)
    assert set(public) == {'schemaVersion','status','selectionPin','sourceCommit','controlGenerationPin',
        'spugInstallationPin','buildPin','build','resourceBuildPin','spugCommit','inputPins'}
    assert public['spugCommit'] == '5651efc5b9972b20bcacb50d0774e5862cbe8e6b'
    assert public['build']['fileCount'] == 147
    assert set(public['build']) == {'fileCount','fileManifestSha256','packageSha256'}
    assert not any(key in json.dumps(public) for key in ('entrySettings','authCredentialRef','newConnections','privatePlan'))


def test_cli_missing_selection_is_nonzero_safe_and_readonly(tmp_path):
    module = subject()
    result = subprocess.run([sys.executable,'-B','-X','utf8',module.__file__,
        '--selection','missing-current-proof.json','--public-summary'],capture_output=True,timeout=15)
    assert result.returncode != 0 and result.stdout == b''
    assert result.stderr.strip() == b'CURRENT_INSTALLATION_VALIDATION_FAILED'


def test_main_manifest_accepts_explicit_verified_build_package_directory():
    import verify_automatic_backup_chain as chain
    build = json.loads((TASK/'release-build-b5fa4c5.json').read_bytes())
    identity = dict(sourceCommit=build['targetCommit'], **{key:build[key] for key in
                    ('packageSha256','fileManifestSha256','fileCount')})
    reference = contract.Records(TASK)
    reference.read('release-build-b5fa4c5.json')
    manifest = chain.main_package_manifest(identity,TASK,PRIVATE,
        build_pin=reference.references['release-build-b5fa4c5.json'])
    assert len(manifest['files']) == 147


def test_ui_preflight_reads_dispatcher_runtime_not_old_rich_name(actual, monkeypatch):
    import prepare_main_program_ui_preflight as ui
    class BoundaryReached(Exception): pass
    reader = subject().BoundDocuments(TASK, actual['verified']['inputPins'])
    selected = json.loads((TASK/OLD_SELECTION).read_bytes())
    runtime = subject().project_runtime(reader, PRIVATE, selected,
        reader.read(selected['verificationInputsPin']), 'PUBLICATION_VERIFICATION')
    def boundary(argv, **kwargs):
        assert runtime['guard']['entryIdentity']['pid'] > 0
        assert kwargs['input'].startswith(('EXPECTED='+repr(runtime['guard'])).encode())
        raise BoundaryReached('stopped before Docker or any external command')
    monkeypatch.setattr(ui.subprocess,'run',boundary)
    with pytest.raises(BoundaryReached):
        ui.spug_observation(dict(spugRuntime=runtime), selected)
