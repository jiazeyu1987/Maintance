"""Import content-bound images without applying an archive's mutable tags.

Projection is private and streaming. Loading is a separate, non-replayable
effect under the restore's real source lock and exact replacement epoch.
"""
import hashlib
import io
import os
from pathlib import Path
import stat
import tarfile

from recovery_engine import RecoveryError, absolute, canonical, parse, require, signature, utc
from recovery_program_activation import _exclusive
from recovery_program_archive import (CHUNK, MAX_MEMBERS, MAX_METADATA, _member_name,
    bounded_tarinfo, inspect_program_archive)
from recovery_program_generation import document


PLAN_FIELDS = {'schemaVersion', 'archiveProgram', 'importPin', 'architecture', 'maxImportBytes'}


def _directory(path, descriptor=None):
    path = absolute(str(path))
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700 and
            info.st_uid == os.geteuid(), 'PROGRAM_IMPORT_DIRECTORY_INVALID')
    identity = info.st_dev, info.st_ino
    if descriptor is not None:
        opened = os.fstat(descriptor)
        require(identity == (opened.st_dev, opened.st_ino), 'PROGRAM_IMPORT_DIRECTORY_CHANGED')
    return path, identity


def _manifest(archive, *, tagless=False):
    members = {}
    for item in archive:
        name = _member_name(item.name)
        require(name not in members and (item.isfile() or item.isdir()) and
                not item.issparse() and item.size >= 0, 'PROGRAM_ARCHIVE_MEMBER_INVALID')
        members[name] = item
        require(len(members) <= MAX_MEMBERS, 'PROGRAM_ARCHIVE_LIMIT_EXCEEDED')
    item = members.get('manifest.json')
    require(item is not None and item.isfile() and 0 < item.size <= MAX_METADATA,
            'PROGRAM_ARCHIVE_METADATA_LIMIT')
    with archive.extractfile(item) as source:
        raw = source.read(MAX_METADATA+1)
    require(len(raw) == item.size, 'PROGRAM_ARCHIVE_INVALID')
    entries = parse(raw)
    require(type(entries) is list and entries, 'PROGRAM_ARCHIVE_INVALID')
    selected = set()
    result = []
    for entry in entries:
        require(type(entry) is dict and set(entry) in ({'Config','RepoTags','Layers'},
                {'Config','RepoTags','Layers','LayerSources'}) and
                type(entry['Config']) is str and type(entry['Layers']) is list and
                all(type(name) is str for name in entry['Layers']), 'PROGRAM_ARCHIVE_INVALID')
        if tagless:
            require(set(entry) == {'Config','RepoTags','Layers'} and entry['RepoTags'] is None,
                    'PROGRAM_IMPORT_TAGS_REJECTED')
        for name in [entry['Config'], *entry['Layers']]:
            require(_member_name(name) == name and name in members and members[name].isfile(),
                    'PROGRAM_ARCHIVE_MEMBER_INVALID')
            selected.add(name)
        result.append(dict(Config=entry['Config'], RepoTags=None, Layers=entry['Layers']))
    if tagless:
        require(set(members) == selected | {'manifest.json'}, 'PROGRAM_IMPORT_TAGS_REJECTED')
    return result, {name:members[name] for name in sorted(selected)}


class _Output:
    def __init__(self, stream, maximum, guard):
        self.stream, self.maximum, self.guard = stream, maximum, guard
        self.bytes, self.checksum = 0, hashlib.sha256()

    def tell(self):
        return self.bytes

    def write(self, value):
        self.guard()
        require(self.bytes+len(value) <= self.maximum, 'PROGRAM_IMPORT_LIMIT_EXCEEDED')
        count = self.stream.write(value)
        require(count == len(value), 'PROGRAM_IMPORT_WRITE_INCOMPLETE')
        self.bytes += count
        self.checksum.update(value)
        return count


class _Input:
    def __init__(self, stream, guard):
        self.stream, self.guard = stream, guard

    def read(self, size):
        self.guard()
        return self.stream.read(min(size, CHUNK))


def prepare_image_import(archive_pin, role_images, directory, *, guard, architecture,
                         max_archive_bytes, max_import_bytes):
    """Create an exclusive tagless tar and immutable preparation receipt.

    The caller accounts for the extra scratch space before preparing a target.
    Partial files are retained and block replay; originals are never rewritten.
    """
    require(callable(guard) and type(max_import_bytes) is int and max_import_bytes > 0,
            'PROGRAM_IMPORT_POLICY_INVALID')
    guard()
    directory, identity = _directory(directory)
    require(not any(directory.iterdir()), 'PROGRAM_IMPORT_ALREADY_PREPARED')
    program = inspect_program_archive(archive_pin, role_images, guard=guard,
        architecture=architecture, max_archive_bytes=max_archive_bytes)
    path = absolute(archive_pin['path'])
    before = signature(path.lstat())
    directory_fd = os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        _directory(directory,directory_fd)
        with path.open('rb') as source:
            require(signature(os.fstat(source.fileno())) == before, 'PROGRAM_ARCHIVE_CHANGED')
            projected_identity = None
            def held():
                guard()
                require(_directory(directory,directory_fd)[1] == identity, 'PROGRAM_IMPORT_DIRECTORY_CHANGED')
                require(signature(os.fstat(source.fileno())) == before and
                        signature(absolute(archive_pin['path']).lstat()) == before, 'PROGRAM_ARCHIVE_CHANGED')
                if projected_identity is not None:
                    require(signature(absolute((directory/'images.tar').as_posix()).lstat()) == projected_identity,
                            'PROGRAM_IMPORT_CHANGED')
            with tarfile.open(fileobj=source,mode='r:',tarinfo=bounded_tarinfo(held)) as original:
                entries,members = _manifest(original)
                held()
                try:
                    descriptor = os.open('images.tar',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                        0o600,dir_fd=directory_fd)
                except FileExistsError as error:
                    raise RecoveryError('PROGRAM_IMPORT_ALREADY_PREPARED') from error
                with os.fdopen(descriptor,'wb') as output:
                    encoded = _Output(output,max_import_bytes,held)
                    with tarfile.open(fileobj=encoded,mode='w',format=tarfile.USTAR_FORMAT) as projected:
                        raw = canonical(entries)
                        info = tarfile.TarInfo('manifest.json'); info.size = len(raw); info.mode = 0o644
                        projected.addfile(info,io.BytesIO(raw))
                        for name,item in members.items():
                            held()
                            info = tarfile.TarInfo(name); info.size = item.size; info.mode = 0o644
                            with original.extractfile(item) as value:
                                projected.addfile(info,_Input(value,held))
                    output.flush(); os.fsync(output.fileno())
                projected_identity = signature((directory/'images.tar').lstat())
                held(); os.fsync(directory_fd)
                reference = dict(path=(directory/'images.tar').as_posix(), bytes=encoded.bytes,
                                 sha256=encoded.checksum.hexdigest())
                imported = inspect_program_archive(reference,role_images,guard=held,
                    architecture=architecture,max_archive_bytes=max_import_bytes)
                require(imported['images'] == program['images'], 'PROGRAM_IMPORT_IMAGES_CHANGED')
                plan = dict(schemaVersion='MainProgramImageImport/v1',archiveProgram=program,
                    importPin=reference,architecture=architecture,maxImportBytes=max_import_bytes)
                return _exclusive(directory/'preparation.json',plan,held)
    except (tarfile.TarError, EOFError, UnicodeError, ValueError) as error:
        raise RecoveryError('PROGRAM_IMPORT_ARCHIVE_INVALID') from error
    finally:
        os.close(directory_fd)


def load_image_import(preparation_pin, *, operation_id, epoch_policy, lock_fd, load,
                      inspect_image, guard):
    """Load once and independently inspect every immutable image identity.

    ``load`` must dispatch the real native Docker command; callbacks in unit
    tests prove the protocol only, never a running Docker installation.
    """
    from recovery_backup_epoch import _assert_lock, read_current
    require(callable(load) and callable(inspect_image) and callable(guard), 'PROGRAM_IMPORT_POLICY_INVALID')
    guard(); _assert_lock(epoch_policy,lock_fd)
    epoch = read_current(epoch_policy,guard=guard)
    require(epoch['state'] == 'REPLACING' and epoch['operationId'] == operation_id,
            'PROGRAM_IMPORT_EPOCH_REQUIRED')
    plan = document(preparation_pin)
    require(type(plan) is dict and set(plan) == PLAN_FIELDS and
            plan['schemaVersion'] == 'MainProgramImageImport/v1' and
            plan['archiveProgram']['schemaVersion'] == 'ArchivedProgramImages/v1',
            'PROGRAM_IMPORT_PLAN_INVALID')
    directory, identity = _directory(Path(preparation_pin['path']).parent)
    require(Path(preparation_pin['path']) == directory/'preparation.json' and
            Path(plan['importPin']['path']) == directory/'images.tar', 'PROGRAM_IMPORT_PLAN_INVALID')
    require(not any((directory/name).exists() for name in ('load-intent.json','load-result.json','load-failure.json')),
            'PROGRAM_IMPORT_ALREADY_LOADED')
    roles = {row['role']:row['imageId'] for row in plan['archiveProgram']['images']}
    require(len(roles) == len(plan['archiveProgram']['images']), 'PROGRAM_IMPORT_PLAN_INVALID')
    path = absolute(plan['importPin']['path']); before = signature(path.lstat())
    imported = inspect_program_archive(plan['importPin'],roles,guard=guard,
        architecture=plan['architecture'],max_archive_bytes=plan['maxImportBytes'])
    require(imported['images'] == plan['archiveProgram']['images'], 'PROGRAM_IMPORT_IMAGES_CHANGED')
    require(signature(path.lstat()) == before, 'PROGRAM_IMPORT_CHANGED')
    with path.open('rb') as source:
        with tarfile.open(fileobj=source,mode='r:',tarinfo=bounded_tarinfo(guard)) as archive:
            _manifest(archive,tagless=True)
    directory_fd = os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        def held():
            guard(); _assert_lock(epoch_policy,lock_fd)
            require(read_current(epoch_policy,guard=guard) == epoch, 'PROGRAM_IMPORT_EPOCH_REQUIRED')
            require(_directory(directory,directory_fd)[1] == identity, 'PROGRAM_IMPORT_DIRECTORY_CHANGED')
            require(document(preparation_pin) == plan, 'PROGRAM_IMPORT_PLAN_CHANGED')
            require(signature(absolute(plan['importPin']['path']).lstat()) == before, 'PROGRAM_IMPORT_CHANGED')
            guard()
        held()
        intent = _exclusive(directory/'load-intent.json',dict(schemaVersion='MainProgramImageLoadIntent/v1',
            operationId=operation_id,epoch=epoch,preparationPin=preparation_pin,startedAt=utc()),held)
        try:
            held(); output = load(path); held()
            require(type(output) is bytes, 'PROGRAM_IMPORT_OUTPUT_INVALID')
            images = {}
            for row in imported['images']:
                held(); actual = inspect_image(row['imageId']); held()
                require(actual['Id'] == row['imageId'] and actual['Os'] == row['os'] and
                        actual['Architecture'] == row['architecture'] and
                        actual['RootFS']['Type'] == 'layers' and actual['RootFS']['Layers'] == row['diffIds'],
                        'PROGRAM_LOADED_IMAGE_CHANGED')
                images[row['imageId']] = actual
            return _exclusive(directory/'load-result.json',dict(schemaVersion='MainProgramImageLoadResult/v1',
                state='LOADED',operationId=operation_id,epoch=epoch,preparationPin=preparation_pin,
                intentPin=intent,images=images,outputBytes=len(output),
                outputSha256=hashlib.sha256(output).hexdigest(),finishedAt=utc()),held)
        except BaseException as error:
            # Failed/unknown effects retain their original intent. Recording
            # failure deliberately cannot require the now-expired guard.
            _exclusive(directory/'load-failure.json',dict(schemaVersion='MainProgramImageLoadFailure/v1',
                state='TERMINAL_UNKNOWN' if getattr(error,'unknown',False) else 'FAILED_RETAINED',
                operationId=operation_id,intentPin=intent,
                failureCode=getattr(error,'code',type(error).__name__),finishedAt=utc()),
                lambda:_directory(directory,directory_fd))
            raise
    finally:
        os.close(directory_fd)
