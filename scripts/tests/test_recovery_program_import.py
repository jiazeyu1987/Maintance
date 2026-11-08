"""Real archives, private files and Linux epochs; callbacks are unit seams only."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile

import pytest

from test_recovery_program_archive import fixture_archive, inspect
from test_recovery_program_generation import case
from test_recovery_program_activation import locked, claim, start
from recovery_engine import RecoveryError, pin, pinned_json

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='real Linux private files/flock required')


def module():
    import recovery_program_import
    return recovery_program_import


def tagged_archive(tmp_path):
    def tagged(rows):
        result = []
        for name, raw in rows:
            if name == 'manifest.json':
                entries = json.loads(raw)
                for index, entry in enumerate(entries):
                    entry['RepoTags'] = ['protected/application:'+str(index)]
                raw = json.dumps(entries).encode()
            result.append((name, raw))
        return result + [('repositories', b'{"protected/application":{}}'),
                         ('index.json', b'{"schemaVersion":2,"manifests":[]}'),
                         ('oci-layout', b'{"imageLayoutVersion":"1.0.0"}'),
                         ('unused.txt', b'not an import input')]
    return fixture_archive(tmp_path, change=tagged)


def prepare(path, roles, directory, **kwargs):
    return module().prepare_image_import(pin(path), roles, directory,
        guard=kwargs.pop('guard', lambda: None), architecture='amd64',
        max_archive_bytes=8*1024*1024,
        max_import_bytes=kwargs.pop('max_import_bytes', 8*1024*1024), **kwargs)


def test_tagless_projection_preserves_content_identities_and_original_bytes(tmp_path):
    path, roles = tagged_archive(tmp_path)
    before = path.read_bytes()
    directory = tmp_path/'import'; directory.mkdir(mode=0o700)
    result = prepare(path, roles, directory)
    plan = pinned_json(result)
    assert plan['schemaVersion'] == 'MainProgramImageImport/v1'
    assert plan['archiveProgram']['archivePin'] == pin(path)
    assert plan['archiveProgram']['images'] == inspect(path, roles)['images']
    imported = plan['importPin']
    assert Path(imported['path']) == directory/'images.tar'
    assert inspect(Path(imported['path']), roles)['images'] == plan['archiveProgram']['images']
    with tarfile.open(imported['path']) as archive:
        manifest = json.load(archive.extractfile('manifest.json'))
        assert all(set(row) == {'Config', 'RepoTags', 'Layers'} and row['RepoTags'] is None for row in manifest)
        selected = {'manifest.json'} | {row['Config'] for row in manifest}
        selected |= {name for row in manifest for name in row['Layers']}
        assert set(archive.getnames()) == selected
    assert path.read_bytes() == before
    assert os.stat(imported['path']).st_mode & 0o777 == 0o600
    assert os.stat(result['path']).st_mode & 0o777 == 0o600


@pytest.mark.parametrize('mode', [0o755, 0o777])
def test_public_output_directory_rejected_before_publication(tmp_path, mode):
    path, roles = tagged_archive(tmp_path)
    directory = tmp_path/'import'; directory.mkdir(mode=mode); directory.chmod(mode)
    with pytest.raises(RecoveryError, match='PROGRAM_IMPORT_DIRECTORY_INVALID'):
        prepare(path, roles, directory)
    assert list(directory.iterdir()) == []


def test_existing_output_is_never_overwritten(tmp_path):
    path, roles = tagged_archive(tmp_path)
    directory = tmp_path/'import'; directory.mkdir(mode=0o700)
    prepare(path, roles, directory)
    before = {p:p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(RecoveryError, match='PROGRAM_IMPORT_ALREADY_PREPARED'):
        prepare(path, roles, directory)
    assert {p:p.read_bytes() for p in directory.iterdir()} == before


def test_outer_pin_mismatch_prevents_output(tmp_path):
    path, roles = tagged_archive(tmp_path)
    directory = tmp_path/'import'; directory.mkdir(mode=0o700)
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_PIN_MISMATCH'):
        module().prepare_image_import(dict(pin(path),sha256='0'*64), roles, directory,
            guard=lambda:None,architecture='amd64',max_archive_bytes=2**20,max_import_bytes=2**20)
    assert list(directory.iterdir()) == []


def test_output_budget_preserves_partial_file_without_success(tmp_path):
    path, roles = tagged_archive(tmp_path)
    directory = tmp_path/'import'; directory.mkdir(mode=0o700)
    with pytest.raises(RecoveryError, match='PROGRAM_IMPORT_LIMIT_EXCEEDED'):
        prepare(path, roles, directory, max_import_bytes=1024)
    assert not (directory/'preparation.json').exists()
    assert (directory/'images.tar').exists()


def test_guard_failure_after_exclusive_creation_is_not_success(tmp_path):
    path, roles = tagged_archive(tmp_path)
    directory = tmp_path/'import'; directory.mkdir(mode=0o700)
    def guard():
        if (directory/'images.tar').exists():
            raise RecoveryError('SHARED_IMPORT_BUDGET_EXHAUSTED')
    with pytest.raises(RecoveryError, match='SHARED_IMPORT_BUDGET_EXHAUSTED'):
        prepare(path, roles, directory, guard=guard)
    assert not (directory/'preparation.json').exists()


def test_original_drift_during_projection_is_rejected(tmp_path):
    path, roles = tagged_archive(tmp_path)
    directory = tmp_path/'import'; directory.mkdir(mode=0o700)
    changed = []
    def guard():
        if (directory/'images.tar').exists() and not changed:
            changed.append(True)
            path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_CHANGED'):
        prepare(path, roles, directory, guard=guard)
    assert not (directory/'preparation.json').exists()


def test_projection_drift_during_receipt_publication_cannot_return_success(tmp_path):
    path, roles = tagged_archive(tmp_path)
    directory = tmp_path/'import'; directory.mkdir(mode=0o700)
    changed = []
    def guard():
        if (directory/'preparation.json').exists() and not changed:
            changed.append(True)
            projected = directory/'images.tar'
            projected.write_bytes(projected.read_bytes()+b'changed')
    with pytest.raises(RecoveryError, match='PROGRAM_IMPORT_CHANGED'):
        prepare(path, roles, directory, guard=guard)


def load_case(case):
    path, roles = tagged_archive(case['root'])
    root = claim(case)
    directory = root/'program-import'; directory.mkdir(mode=0o700)
    prepared = prepare(path, roles, directory)
    plan = pinned_json(prepared)
    images = {row['imageId']:dict(Id=row['imageId'], Os=row['os'], Architecture=row['architecture'],
        RootFS=dict(Type='layers',Layers=row['diffIds'])) for row in plan['archiveProgram']['images']}
    calls = []
    def loader(import_path):
        calls.append(Path(import_path))
        return b'Loaded image ID: verified unit protocol seam'
    return root,directory,prepared,images,calls,loader


def invoke(case, prepared, fd, loader, images, **kwargs):
    return module().load_image_import(prepared,operation_id=kwargs.pop('operation_id','restore-1'),
        epoch_policy=case['epoch'],lock_fd=fd,load=loader,inspect_image=images.__getitem__,
        guard=kwargs.pop('guard',lambda:None),**kwargs)


def test_loading_requires_same_real_epoch_and_records_verified_image_observation(case):
    root,directory,prepared,images,calls,loader = load_case(case)
    with locked(case) as fd:
        epoch = start(case,root,fd)
        receipt = invoke(case,prepared,fd,loader,images)
    result = pinned_json(receipt)
    assert result['state'] == 'LOADED' and result['operationId'] == 'restore-1'
    assert result['epoch'] == epoch and result['preparationPin'] == prepared
    assert result['images'] == images
    assert calls == [directory/'images.tar']
    assert not (root/'replacement-result.json').exists()


@pytest.mark.parametrize('problem', ['unheld','ready','foreign-operation'])
def test_no_import_effect_without_exact_real_replacement_lock_and_operation(case, problem):
    root,directory,prepared,images,calls,loader = load_case(case)
    with locked(case,held=problem!='unheld') as fd:
        if problem != 'ready':
            if problem=='unheld':
                with locked(case) as real_fd: start(case,root,real_fd)
            else: start(case,root,fd)
        with pytest.raises((RecoveryError, ValueError), match='BACKUP_EPOCH_|PROGRAM_IMPORT_EPOCH_REQUIRED'):
            invoke(case,prepared,fd,loader,images,operation_id='other' if problem=='foreign-operation' else 'restore-1')
    assert calls == [] and not (directory/'load-intent.json').exists()


def test_image_drift_after_load_remains_failed_and_replay_is_rejected(case):
    root,directory,prepared,images,calls,loader = load_case(case)
    images[next(iter(images))]['RootFS']['Layers'] = []
    with locked(case) as fd:
        start(case,root,fd)
        with pytest.raises(RecoveryError, match='PROGRAM_LOADED_IMAGE_CHANGED'):
            invoke(case,prepared,fd,loader,images)
        assert pinned_json(pin(directory/'load-failure.json'))['state'] == 'FAILED_RETAINED'
        with pytest.raises(RecoveryError, match='PROGRAM_IMPORT_ALREADY_LOADED'):
            invoke(case,prepared,fd,loader,images)
    assert len(calls) == 1 and not (directory/'load-result.json').exists()


def test_changed_projection_pin_is_rejected_before_import_effect(case):
    root,directory,prepared,images,calls,loader = load_case(case)
    (directory/'images.tar').write_bytes(b'changed')
    with locked(case) as fd:
        start(case,root,fd)
        with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_PIN_MISMATCH'):
            invoke(case,prepared,fd,loader,images)
    assert calls == []


def test_re_pinned_import_with_tags_is_rejected_before_effect(case):
    from test_recovery_program_generation import write
    root,directory,prepared,images,calls,loader = load_case(case)
    plan = pinned_json(prepared)
    original = Path(plan['archiveProgram']['archivePin']['path'])
    projected = directory/'images.tar'; projected.write_bytes(original.read_bytes())
    plan['importPin'] = pin(projected)
    changed = write(Path(prepared['path']),plan)
    with locked(case) as fd:
        start(case,root,fd)
        with pytest.raises(RecoveryError, match='PROGRAM_IMPORT_TAGS_REJECTED'):
            invoke(case,changed,fd,loader,images)
    assert calls == [] and not (directory/'load-intent.json').exists()


def test_unknown_load_retains_failure_and_cannot_be_replayed(case):
    root,directory,prepared,images,calls,loader = load_case(case)
    def unknown(path):
        calls.append(Path(path))
        raise RecoveryError('IMPORT_NATIVE_EXIT_UNKNOWN',unknown=True)
    with locked(case) as fd:
        start(case,root,fd)
        with pytest.raises(RecoveryError, match='IMPORT_NATIVE_EXIT_UNKNOWN'):
            invoke(case,prepared,fd,unknown,images)
        result = pinned_json(pin(directory/'load-failure.json'))
        assert result['state'] == 'TERMINAL_UNKNOWN'
        with pytest.raises(RecoveryError, match='PROGRAM_IMPORT_ALREADY_LOADED'):
            invoke(case,prepared,fd,unknown,images)
    assert len(calls) == 1 and not (directory/'load-result.json').exists()
