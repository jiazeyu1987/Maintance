"""Remove only selected operation-owned staging, with durable deletion evidence.

Callers must establish successful archive readback or restore before calling.
Linux directory descriptors prevent deletion through symlinks or swapped parents.
Operation receipts and archived NAS bytes are never cleanup targets.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
from contextlib import ExitStack
from datetime import datetime, timezone


class StagingCleanupError(RuntimeError):
    code = 'STAGING_CLEANUP_FAILED'


def require(value):
    if not value:
        raise StagingCleanupError('STAGING_CLEANUP_UNSAFE_OR_CHANGED')


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink)


def capture_paths(root):
    return [name for name in ('payload', 'original-configs', 'recovery-materials',
            'semantic-capture', 'scratch-before', 'scratch-after', 'scratch-affected')
            if os.path.lexists(Path(root)/name)]


def restore_paths(root):
    paths = []
    for directory in Path(root).iterdir():
        if re.fullmatch(r'database-\d{3}', directory.name):
            require(directory.is_dir() and not directory.is_symlink())
            for item in directory.iterdir():
                if item.name in ('archive-sql.private.gz', 'expanded.sql', 'incremental.sql',
                                 'full.private.gz', 'full.sql', 'incremental.private.gz',
                                 'database-readback') or re.fullmatch(r'binlog-\d{3}\.sql', item.name):
                    paths.append(item.relative_to(root).as_posix())
        elif re.fullmatch(r'objects(?:-\d{3})?', directory.name):
            require(directory.is_dir() and not directory.is_symlink())
            # Keep the export receipt, inventory and version mappings as evidence.
            item = directory/'physical-export'/'objects'
            if os.path.lexists(item):
                paths.append(item.relative_to(root).as_posix())
    return paths


def cleanup(root, paths, operation_id, *, guard, archived_files=None, scratch_paths=(), verify_files=True):
    root = Path(root).absolute()
    require(root.resolve(strict=True) == root)
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', operation_id))
    require(root.name == operation_id)
    require(len(paths) == len(set(paths)))
    for name in paths:
        p = PurePosixPath(name)
        require(not p.is_absolute() and p.parts and all(x not in ('', '.', '..') for x in p.parts))
        require(p.as_posix() == name)
    require(all(not (a != b and PurePosixPath(a) in PurePosixPath(b).parents)
                for a in paths for b in paths))
    if not verify_files:
        # ponytail: selected task-owned roots only; no file inventory or identity pass.
        targets = [root.joinpath(*PurePosixPath(name).parts) for name in paths]
        require(all(path.resolve(strict=True).is_relative_to(root) for path in targets))
        evidence = dict(schemaVersion='OperationStagingCleanup/v1', operationId=operation_id,
            root=str(root), selectedPaths=paths, verificationState='NOT_PERFORMED')
        def record(name, value):
            with (root/name).open('x', encoding='utf-8') as stream:
                json.dump(value, stream, sort_keys=True)
        record('staging-cleanup-intent.json', dict(evidence, state='PLANNED'))
        for target in targets:
            guard()
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        record('staging-cleanup.json', dict(evidence, state='SUCCEEDED',
            finishedAt=datetime.now(timezone.utc).isoformat()))
        return root/'staging-cleanup.json'
    require(os.name == 'posix')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    files, directories = [], []
    guard()
    with ExitStack() as stack:
        root_fd = os.open(root, flags); stack.callback(os.close, root_fd)
        device = os.fstat(root_fd).st_dev

        def parent_fd(relative, contexts):
            fd = root_fd
            for part in PurePosixPath(relative).parts[:-1]:
                fd = os.open(part, flags, dir_fd=fd)
                contexts.callback(os.close, fd)
                require(os.fstat(fd).st_dev == device)
            return fd

        def collect(fd, name, relative):
            guard()
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(info.st_dev == device)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, flags, dir_fd=fd)
                try:
                    require(identity(os.fstat(child)) == identity(info))
                    for entry in sorted(os.listdir(child)):
                        collect(child, entry, relative+'/'+entry)
                finally:
                    os.close(child)
                directories.append((relative, info.st_dev, info.st_ino))
            else:
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
                checksum = None
                if archived_files is not None and not any(
                        relative == p or relative.startswith(p+'/') for p in scratch_paths):
                    checksum = hashlib.sha256()
                    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                    with os.fdopen(handle, 'rb') as stream:
                        require(identity(os.fstat(stream.fileno())) == identity(info))
                        while True:
                            guard()
                            block = stream.read(1024*1024)
                            if not block:
                                break
                            checksum.update(block)
                        require(identity(os.fstat(stream.fileno())) == identity(info))
                    checksum = checksum.hexdigest()
                    require(archived_files.get(relative) == (info.st_size, checksum))
                files.append((relative, identity(info), info.st_size, checksum))

        for name in paths:
            with ExitStack() as parents:
                collect(parent_fd(name, parents), PurePosixPath(name).name, name)

        def receipt(name, value):
            raw = (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=root_fd)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.fsync(root_fd)

        evidence = dict(schemaVersion='OperationStagingCleanup/v1', operationId=operation_id,
            root=str(root), selectedPaths=paths,
            files=[dict(path=p, bytes=size, **({'sha256': sha} if sha is not None else {}))
                   for p, _, size, sha in files],
            deletedBytes=sum(row[2] for row in files), deletedFiles=len(files))
        receipt('staging-cleanup-intent.json', dict(evidence, state='PLANNED'))
        guard()
        require(os.stat(root).st_ino == os.fstat(root_fd).st_ino)
        for relative, expected, _, _ in files:
            with ExitStack() as parents:
                fd = parent_fd(relative, parents); name = PurePosixPath(relative).name
                require(identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) == expected)
                os.unlink(name, dir_fd=fd); os.fsync(fd)
        for relative, dev, inode in directories:
            with ExitStack() as parents:
                fd = parent_fd(relative, parents); name = PurePosixPath(relative).name
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == (dev, inode))
                os.rmdir(name, dir_fd=fd); os.fsync(fd)
        require(not any(os.path.lexists(root/name) for name in paths))
        receipt('staging-cleanup.json', dict(evidence, state='SUCCEEDED',
            finishedAt=datetime.now(timezone.utc).isoformat()))
    return root/'staging-cleanup.json'
