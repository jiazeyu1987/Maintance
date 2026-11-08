"""Offline program identity must be established before any target mutation."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/recovery'))
from recovery_engine import RecoveryError, pin


def fixture_archive(tmp_path, *, change=None, extra=None):
    members = []
    entries = []
    identities = {}
    for role in ('backend', 'frontend'):
        layer = (role+' real layer bytes').encode()
        config = {'os': 'linux', 'architecture': 'amd64',
                  'rootfs': {'type': 'layers', 'diff_ids': ['sha256:'+hashlib.sha256(layer).hexdigest()]}}
        raw = json.dumps(config, separators=(',', ':')).encode()
        name = hashlib.sha256(raw).hexdigest()+'.json'
        identities[role] = 'sha256:'+hashlib.sha256(raw).hexdigest()
        members.extend([(name, raw), (role+'/layer.tar', layer)])
        entries.append({'Config': name, 'RepoTags': None, 'Layers': [role+'/layer.tar']})
    members.append(('manifest.json', json.dumps(entries).encode()))
    if change:
        members = change(members)
    path = tmp_path/'images.tar'
    with tarfile.open(path, 'w') as archive:
        for name, raw in members:
            info = tarfile.TarInfo(name); info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        if extra:
            info = tarfile.TarInfo(extra[0]); info.type = extra[1]; info.linkname = 'manifest.json'
            archive.addfile(info)
    return path, identities


def inspect(path, roles, **kwargs):
    from recovery_program_archive import inspect_program_archive
    return inspect_program_archive(kwargs.pop('archive_pin', pin(path)), roles,
        guard=kwargs.pop('guard', lambda: None), architecture='amd64',
        max_archive_bytes=kwargs.pop('max_archive_bytes', 8*1024*1024), **kwargs)


def test_complete_program_roles_have_content_bound_platform_and_layers(tmp_path):
    path, roles = fixture_archive(tmp_path)
    result = inspect(path, roles)
    assert result['schemaVersion'] == 'ArchivedProgramImages/v1'
    assert result['archivePin'] == pin(path)
    assert {row['role']: row['imageId'] for row in result['images']} == roles
    assert all(row['os'] == 'linux' and row['architecture'] == 'amd64'
               and len(row['diffIds']) == 1 for row in result['images'])
    assert sorted(p.name for p in tmp_path.iterdir()) == ['images.tar']


def test_layer_corruption_rejected_even_when_outer_pin_matches(tmp_path):
    path, roles = fixture_archive(tmp_path, change=lambda rows: [
        (name, b'corrupt layer' if name == 'backend/layer.tar' else raw) for name, raw in rows])
    with pytest.raises(RecoveryError, match='PROGRAM_LAYER_DIGEST_MISMATCH'):
        inspect(path, roles)


def test_missing_layer_rejected(tmp_path):
    path, roles = fixture_archive(tmp_path, change=lambda rows: [r for r in rows if r[0] != 'frontend/layer.tar'])
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_MEMBER_INVALID'):
        inspect(path, roles)


def test_config_identity_mismatch_rejected(tmp_path):
    path, roles = fixture_archive(tmp_path, change=lambda rows: [
        (name, raw+b' ' if name.endswith('.json') and name != 'manifest.json' else raw) for name, raw in rows])
    with pytest.raises(RecoveryError, match='PROGRAM_IMAGE_ID_MISMATCH'):
        inspect(path, roles)


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'a/../escape', 'a//b', 'a\\b', './manifest.json'])
def test_unsafe_member_names_are_not_extracted(tmp_path, name):
    path, roles = fixture_archive(tmp_path, change=lambda rows: rows+[(name, b'not extracted')])
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_MEMBER_INVALID'):
        inspect(path, roles)
    assert not (tmp_path.parent/'escape').exists()


@pytest.mark.parametrize('kind', [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE])
def test_links_and_special_files_rejected(tmp_path, kind):
    path, roles = fixture_archive(tmp_path, extra=('unsafe', kind))
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_MEMBER_INVALID'):
        inspect(path, roles)


def test_duplicate_manifest_rejected(tmp_path):
    path, roles = fixture_archive(tmp_path, change=lambda rows: rows+[rows[-1]])
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_MEMBER_INVALID'):
        inspect(path, roles)


def test_outer_pin_mismatch_rejected(tmp_path):
    path, roles = fixture_archive(tmp_path)
    wrong = dict(pin(path), sha256='0'*64)
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_PIN_MISMATCH'):
        inspect(path, roles, archive_pin=wrong)


def test_archive_limit_checked_before_reading(tmp_path):
    path, roles = fixture_archive(tmp_path)
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_LIMIT_EXCEEDED'):
        inspect(path, roles, max_archive_bytes=path.stat().st_size-1)


def test_unknown_architecture_rejected(tmp_path):
    path, roles = fixture_archive(tmp_path)
    from recovery_program_archive import inspect_program_archive
    with pytest.raises(RecoveryError, match='PROGRAM_IMAGE_PLATFORM_MISMATCH'):
        inspect_program_archive(pin(path), roles, guard=lambda: None, architecture='arm64', max_archive_bytes=2**20)


def test_duplicate_json_members_rejected(tmp_path):
    path, roles = fixture_archive(tmp_path, change=lambda rows: [
        (name, b'[{"Config":"a","Config":"b","RepoTags":null,"Layers":[]}]'
         if name == 'manifest.json' else raw) for name, raw in rows])
    with pytest.raises(RecoveryError, match='DUPLICATE_JSON_KEY'):
        inspect(path, roles)


def test_guard_failure_propagates_without_success(tmp_path):
    path, roles = fixture_archive(tmp_path)
    def guard():
        raise RecoveryError('ORIGINAL_LEASE_CHANGED')
    with pytest.raises(RecoveryError, match='ORIGINAL_LEASE_CHANGED'):
        inspect(path, roles, guard=guard)


def test_same_image_for_two_roles_is_allowed_only_with_exact_identity(tmp_path):
    path, original = fixture_archive(tmp_path)
    roles = dict(original, auxiliary=original['backend'])
    result = inspect(path, roles)
    assert {row['role']: row['imageId'] for row in result['images']} == roles


def test_unexpected_extra_image_is_not_silently_accepted(tmp_path):
    path, roles = fixture_archive(tmp_path)
    with pytest.raises(RecoveryError, match='PROGRAM_IMAGE_ID_MISMATCH'):
        inspect(path, {'backend': roles['backend']})


def test_changed_file_during_read_is_rejected(tmp_path):
    path, roles = fixture_archive(tmp_path)
    reference = pin(path)
    calls = 0
    def guard():
        nonlocal calls
        calls += 1
        if calls == 3:
            stamp = path.stat()
            os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns+1_000_000_000))
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_CHANGED'):
        inspect(path, roles, archive_pin=reference, guard=guard)


@pytest.mark.parametrize('roles', [{}, {'backend': 'tag:latest'}, {'backend': 3}, []])
def test_invalid_role_binding_rejected(tmp_path, roles):
    path, _ = fixture_archive(tmp_path)
    with pytest.raises(RecoveryError, match='PROGRAM_ROLE_IMAGES_INVALID'):
        inspect(path, roles)


def test_truncated_tar_rejected(tmp_path):
    path, roles = fixture_archive(tmp_path)
    path.write_bytes(path.read_bytes()[:700])
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_INVALID'):
        inspect(path, roles)


def test_growing_file_stops_at_original_byte_limit(tmp_path):
    path, roles = fixture_archive(tmp_path)
    reference = pin(path)
    calls = 0
    def guard():
        nonlocal calls
        calls += 1
        if calls == 2:
            with path.open('ab') as stream:
                stream.write(b'x'*2048)
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_LIMIT_EXCEEDED'):
        inspect(path, roles, archive_pin=reference, guard=guard)


def test_oversized_extension_header_rejected_before_metadata_allocation(tmp_path):
    path, roles = fixture_archive(tmp_path)
    extension = tarfile.TarInfo('extension'); extension.type = tarfile.XHDTYPE
    extension.size = 16*1024*1024+1
    path.write_bytes(extension.tobuf()+b'\0'*1024)
    with pytest.raises(RecoveryError, match='PROGRAM_ARCHIVE_METADATA_LIMIT'):
        inspect(path, roles)


def test_bounded_pax_metadata_remains_readable(tmp_path):
    path, roles = fixture_archive(tmp_path)
    original = path.read_bytes()
    with tarfile.open(fileobj=io.BytesIO(original)) as source:
        members = [(row, source.extractfile(row).read()) for row in source]
    with tarfile.open(path, 'w', format=tarfile.PAX_FORMAT) as destination:
        for row, raw in members:
            row.pax_headers = {'comment': 'ordinary export metadata'}
            destination.addfile(row, io.BytesIO(raw))
    assert len(inspect(path, roles)['images']) == 2


def descriptor_manifest(rows, mutate=lambda value: value):
    payloads = dict(rows)
    manifest = json.loads(payloads['manifest.json'])
    for entry in manifest:
        entry['LayerSources'] = {}
        for name in entry['Layers']:
            raw = payloads[name]
            identity = 'sha256:'+hashlib.sha256(raw).hexdigest()
            entry['LayerSources'][identity] = dict(mediaType='application/vnd.oci.image.layer.v1.tar',
                                                   size=len(raw), digest=identity)
    mutate(manifest)
    return [(name, json.dumps(manifest).encode() if name == 'manifest.json' else raw) for name, raw in rows]


def test_docker_layer_sources_are_bound_to_exact_uncompressed_content(tmp_path):
    path, roles = fixture_archive(tmp_path, change=descriptor_manifest)
    assert len(inspect(path, roles)['images']) == 2


@pytest.mark.parametrize('field,value', [('size', 1), ('digest', 'sha256:'+'0'*64),
                                       ('mediaType', 'application/vnd.oci.image.layer.v1.tar+gzip'),
                                       ('urls', ['https://unexpected.invalid/layer'])])
def test_layer_source_descriptor_drift_rejected(tmp_path, field, value):
    def mutate(manifest):
        next(iter(manifest[0]['LayerSources'].values()))[field] = value
    path, roles = fixture_archive(tmp_path, change=lambda rows: descriptor_manifest(rows, mutate))
    with pytest.raises(RecoveryError, match='PROGRAM_LAYER_DESCRIPTOR_MISMATCH'):
        inspect(path, roles)
