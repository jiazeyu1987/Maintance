"""Read-only, content-bound Docker program archives for restoration planning.

This module neither loads images nor creates containers. A caller must keep its
archive lease and deadline guard held, and revalidate the resulting pin before
any later effect. Program selection never resolves mutable repository tags.
"""
import hashlib
import os
from pathlib import PurePosixPath
import re
import tarfile

from recovery_engine import RecoveryError, absolute, parse, require, signature

CHUNK = 1024 * 1024
MAX_MEMBERS = 100000
MAX_METADATA = 16 * CHUNK
IMAGE_ID = re.compile(r'sha256:[0-9a-f]{64}\Z')


def _member_name(name):
    require(type(name) is str and name and '\\' not in name and
            not any(ord(char) < 32 for char in name) and
            not PurePosixPath(name).is_absolute() and
            all(part not in ('', '.', '..') for part in name.rstrip('/').split('/')) and
            str(PurePosixPath(name)) == name.rstrip('/'), 'PROGRAM_ARCHIVE_MEMBER_INVALID')
    return name.rstrip('/')


def _hash_stream(stream, guard, limit):
    checksum = hashlib.sha256()
    count = 0
    while True:
        guard()
        chunk = stream.read(min(CHUNK, limit-count+1))
        if not chunk:
            break
        checksum.update(chunk)
        count += len(chunk)
        require(count <= limit, 'PROGRAM_ARCHIVE_LIMIT_EXCEEDED')
    return count, checksum.hexdigest()


def _inspect_contents(stream, roles, architecture, guard):
    headers = 0
    depth = 0

    class BoundedTarInfo(tarfile.TarInfo):
        def _proc_member(self, archive):
            # tarfile processes extension bodies before yielding a member. The
            # factory hook enforces limits before that allocation/recursion.
            nonlocal headers, depth
            guard()
            headers += 1
            depth += 1
            require(headers <= MAX_MEMBERS and depth <= 16, 'PROGRAM_ARCHIVE_LIMIT_EXCEEDED')
            if self.type in (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.SOLARIS_XHDTYPE,
                             tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK):
                require(0 <= self.size <= MAX_METADATA, 'PROGRAM_ARCHIVE_METADATA_LIMIT')
            try:
                return super()._proc_member(archive)
            finally:
                depth -= 1

    with tarfile.open(fileobj=stream, mode='r:', tarinfo=BoundedTarInfo) as archive:
        members = {}
        for item in archive:
            guard()
            name = _member_name(item.name)
            require(name not in members and (item.isfile() or item.isdir()) and
                    not item.issparse() and item.size >= 0, 'PROGRAM_ARCHIVE_MEMBER_INVALID')
            members[name] = item
            require(len(members) <= MAX_MEMBERS, 'PROGRAM_ARCHIVE_LIMIT_EXCEEDED')

        def member(name):
            require(_member_name(name) == name, 'PROGRAM_ARCHIVE_MEMBER_INVALID')
            item = members.get(name)
            require(item is not None and item.isfile(), 'PROGRAM_ARCHIVE_MEMBER_INVALID')
            return item

        def document(name):
            guard()
            item = member(name)
            require(0 < item.size <= MAX_METADATA, 'PROGRAM_ARCHIVE_METADATA_LIMIT')
            with archive.extractfile(item) as source:
                raw = source.read(MAX_METADATA+1)
            require(len(raw) == item.size, 'PROGRAM_ARCHIVE_INVALID')
            guard()
            return parse(raw), raw

        manifest, _ = document('manifest.json')
        require(type(manifest) is list and len(manifest) == len(set(roles.values())),
                'PROGRAM_IMAGE_ID_MISMATCH')
        found = {}
        verified_layers = {}
        for entry in manifest:
            require(type(entry) is dict and set(entry) in ({'Config', 'RepoTags', 'Layers'},
                    {'Config', 'RepoTags', 'Layers', 'LayerSources'}) and
                    type(entry['Config']) is str and type(entry['Layers']) is list and
                    all(type(name) is str for name in entry['Layers']) and
                    len(entry['Layers']) == len(set(entry['Layers'])) and
                    (entry['RepoTags'] is None or type(entry['RepoTags']) is list and
                     all(type(tag) is str for tag in entry['RepoTags'])), 'PROGRAM_ARCHIVE_INVALID')
            config, raw = document(entry['Config'])
            image_id = 'sha256:'+hashlib.sha256(raw).hexdigest()
            require(image_id in roles.values() and image_id not in found, 'PROGRAM_IMAGE_ID_MISMATCH')
            require(type(config) is dict and config.get('os') == 'linux' and
                    config.get('architecture') == architecture, 'PROGRAM_IMAGE_PLATFORM_MISMATCH')
            rootfs = config.get('rootfs')
            require(type(rootfs) is dict and rootfs.get('type') == 'layers' and
                    type(rootfs.get('diff_ids')) is list and
                    all(type(value) is str and IMAGE_ID.fullmatch(value) for value in rootfs['diff_ids']) and
                    len(rootfs['diff_ids']) == len(entry['Layers']), 'PROGRAM_IMAGE_LAYERS_INVALID')
            descriptors = entry.get('LayerSources')
            if 'LayerSources' in entry:
                require(type(descriptors) is dict and set(descriptors) == set(rootfs['diff_ids']),
                        'PROGRAM_LAYER_DESCRIPTOR_MISMATCH')
            for name, expected in zip(entry['Layers'], rootfs['diff_ids']):
                guard()
                item = member(name)
                if descriptors is not None:
                    require(descriptors[expected] == dict(mediaType='application/vnd.oci.image.layer.v1.tar',
                            size=item.size, digest=expected) and type(descriptors[expected].get('size')) is int,
                            'PROGRAM_LAYER_DESCRIPTOR_MISMATCH')
                if name not in verified_layers:
                    with archive.extractfile(item) as layer:
                        count, checksum = _hash_stream(layer, guard, item.size)
                    require(count == item.size, 'PROGRAM_ARCHIVE_INVALID')
                    verified_layers[name] = 'sha256:'+checksum
                require(verified_layers[name] == expected, 'PROGRAM_LAYER_DIGEST_MISMATCH')
            found[image_id] = dict(imageId=image_id, os='linux', architecture=architecture,
                                  diffIds=rootfs['diff_ids'])
        require(set(found) == set(roles.values()), 'PROGRAM_IMAGE_ID_MISMATCH')
        return [dict(role=role, **found[identity]) for role, identity in sorted(roles.items())]


def inspect_program_archive(archive_pin, role_images, *, guard, architecture, max_archive_bytes):
    """Verify the outer pin, exact image configs and all uncompressed layers."""
    require(type(role_images) is dict and role_images and
            all(type(role) is str and re.fullmatch('[a-z][a-z0-9_-]{0,63}', role) and
                type(value) is str and IMAGE_ID.fullmatch(value) for role, value in role_images.items()),
            'PROGRAM_ROLE_IMAGES_INVALID')
    roles = dict(role_images)
    require(type(archive_pin) is dict and set(archive_pin) == {'path', 'bytes', 'sha256'} and
            type(archive_pin['path']) is str and type(archive_pin['bytes']) is int and
            archive_pin['bytes'] > 0 and type(archive_pin['sha256']) is str and
            re.fullmatch('[0-9a-f]{64}', archive_pin['sha256']), 'PROGRAM_ARCHIVE_PIN_INVALID')
    reference = dict(archive_pin)
    require(callable(guard) and type(architecture) is str and
            re.fullmatch('[a-z0-9_]{1,32}', architecture) and type(max_archive_bytes) is int and
            max_archive_bytes > 0, 'PROGRAM_ARCHIVE_POLICY_INVALID')
    require(reference['bytes'] <= max_archive_bytes, 'PROGRAM_ARCHIVE_LIMIT_EXCEEDED')
    guard()
    path = absolute(reference['path'])
    before = signature(path.lstat())
    require(before[2] == reference['bytes'], 'PROGRAM_ARCHIVE_PIN_MISMATCH')
    try:
        with path.open('rb') as stream:
            require(signature(os.fstat(stream.fileno())) == before, 'PROGRAM_ARCHIVE_CHANGED')
            size, checksum = _hash_stream(stream, guard, reference['bytes'])
            require(size == reference['bytes'] and checksum == reference['sha256'],
                    'PROGRAM_ARCHIVE_PIN_MISMATCH')
            stream.seek(0)
            images = _inspect_contents(stream, roles, architecture, guard)
            guard()
            require(signature(os.fstat(stream.fileno())) == before and
                    signature(absolute(reference['path']).lstat()) == before, 'PROGRAM_ARCHIVE_CHANGED')
    except (tarfile.TarError, EOFError, UnicodeError, ValueError) as error:
        raise RecoveryError('PROGRAM_ARCHIVE_INVALID') from error
    return dict(schemaVersion='ArchivedProgramImages/v1', archivePin=reference, images=images)
